// ---------- AutoLang compiler (JS) ----------
const KEYWORDS = new Set(["START","END","MOVE","TURN","LED","WAIT","IF","THEN",
  "STOP","RUN","TASK","FORWARD","BACKWARD","LEFT","RIGHT","ON","OFF","BLINK",
  "OBSTACLE","DETECT","SENSOR"]);

function tokenize(src) {
  const toks = [];
  src.split("\n").forEach((raw, i) => {
    const line = raw.split("#")[0].trim();
    if (!line) return;
    for (const w of line.split(/\s+/)) {
      const up = w.toUpperCase();
      if (KEYWORDS.has(up)) toks.push({type:"KEYWORD", value:up, line:i+1});
      else if (/^-?\d+$/.test(w)) toks.push({type:"NUMBER", value:+w, line:i+1});
      else if (/^[A-Za-z_]\w*$/.test(w)) toks.push({type:"IDENT", value:w, line:i+1});
      else throw new Error(`Line ${i+1}: Unexpected token '${w}'`);
    }
    toks.push({type:"NEWLINE", value:"\\n", line:i+1});
  });
  toks.push({type:"EOF", value:null, line:0});
  return toks;
}

class Parser {
  constructor(t){ this.t=t; this.p=0; }
  peek(o=0){ return this.t[this.p+o]; }
  eat(){ return this.t[this.p++]; }
  expect(type, value){
    const x = this.peek();
    if (x.type!==type || (value && x.value!==value))
      throw new Error(`Line ${x.line}: expected ${value||type}, got '${x.value}'`);
    return this.eat();
  }
  skipNL(){ while(this.peek().type==="NEWLINE") this.eat(); }
  parse(){
    this.skipNL();
    this.expect("KEYWORD","START"); this.expect("NEWLINE");
    const body=[], tasks=[];
    while(true){
      this.skipNL();
      const t=this.peek();
      if (t.type==="KEYWORD" && t.value==="END") break;
      if (t.type==="EOF") throw new Error("Missing END");
      if (t.type==="KEYWORD" && t.value==="TASK") tasks.push(this.task());
      else body.push(this.stmt());
    }
    this.expect("KEYWORD","END");
    return {kind:"Program", body, tasks};
  }
  stmt(){
    const t=this.peek();
    const map={MOVE:"move",TURN:"turn",LED:"led",WAIT:"wait",IF:"if_",STOP:"stop",RUN:"run"};
    const fn=map[t.value];
    if(!fn) throw new Error(`Line ${t.line}: unknown '${t.value}'`);
    const n=this[fn]();
    if(this.peek().type==="NEWLINE") this.eat();
    return n;
  }
  move(){const l=this.eat().line;const d=this.expect("KEYWORD").value;
    const n=this.expect("NUMBER").value;return {kind:"Move",direction:d,distance:n,line:l};}
  turn(){const l=this.eat().line;const d=this.expect("KEYWORD").value;
    const a=this.expect("NUMBER").value;return {kind:"Turn",direction:d,angle:a,line:l};}
  led(){const l=this.eat().line;const m=this.expect("KEYWORD").value;
    if(m==="BLINK"){const n=this.expect("NUMBER").value;return {kind:"Led",mode:"BLINK",times:n,line:l};}
    return {kind:"Led",mode:m,line:l};}
  wait(){const l=this.eat().line;return {kind:"Wait",seconds:this.expect("NUMBER").value,line:l};}
  stop(){const l=this.eat().line;return {kind:"Stop",line:l};}
  run(){const l=this.eat().line;return {kind:"Run",name:this.expect("IDENT").value,line:l};}
  if_(){const l=this.eat().line;const cond=[];
    while(this.peek().type==="KEYWORD" && this.peek().value!=="THEN") cond.push(this.eat().value);
    this.expect("KEYWORD","THEN");
    const action=this.stmt();
    return {kind:"If",condition:cond.join(" "),action,line:l};}
  task(){const l=this.eat().line;const name=this.expect("IDENT").value;this.expect("NEWLINE");
    const body=[];
    while(true){this.skipNL();const t=this.peek();
      if(t.type==="KEYWORD" && (t.value==="END"||t.value==="TASK")) break;
      if(t.type==="EOF") break;
      body.push(this.stmt());}
    return {kind:"Task",name,body,line:l};}
}

function semantic(ast){
  const tasks=new Set(ast.tasks.map(t=>t.name));
  const walk=n=>{
    if(n.kind==="Move" && n.distance<=0)
      throw new Error(`Line ${n.line}: Invalid movement distance: ${n.distance}. Distance must be positive.`);
    if(n.kind==="Turn" && (n.angle<0||n.angle>360))
      throw new Error(`Line ${n.line}: Invalid angle ${n.angle}`);
    if(n.kind==="Led" && n.mode==="BLINK" && n.times<=0)
      throw new Error(`Line ${n.line}: LED BLINK times must be > 0`);
    if(n.kind==="Run" && !tasks.has(n.name))
      throw new Error(`Line ${n.line}: Undefined task '${n.name}'`);
    if(n.kind==="If") walk(n.action);
  };
  ast.tasks.forEach(t=>t.body.forEach(walk));
  ast.body.forEach(walk);
}

function lower(ast){
  const tasks={};
  ast.tasks.forEach(t=>tasks[t.name]=t.body.map(lowerStmt));
  const ins=[];
  ast.body.forEach(s=>{
    const x=lowerStmt(s);
    if(x.op==="RUN") (tasks[x.args[0]]||[]).forEach(y=>ins.push(y));
    else ins.push(x);
  });
  return ins;
}
function lowerStmt(n){
  switch(n.kind){
    case "Move": return {op:n.direction==="FORWARD"?"MOVE_FORWARD":"MOVE_BACKWARD",args:[n.distance],line:n.line};
    case "Turn": return {op:n.direction==="LEFT"?"TURN_LEFT":"TURN_RIGHT",args:[n.angle],line:n.line};
    case "Led":  return n.mode==="BLINK"?{op:"LED_BLINK",args:[n.times],line:n.line}
                    :{op:"LED_"+n.mode,args:[],line:n.line};
    case "Wait": return {op:"WAIT",args:[n.seconds],line:n.line};
    case "Stop": return {op:"STOP",args:[],line:n.line};
    case "Run":  return {op:"RUN",args:[n.name],line:n.line};
    case "If":   return {op:"IF",args:[n.condition, lowerStmt(n.action)],line:n.line};
  }
}

function optimize(ir){
  const out=[];
  for(const i of ir){
    const last=out[out.length-1];
    if(last && last.op===i.op && ["MOVE_FORWARD","MOVE_BACKWARD","TURN_LEFT","TURN_RIGHT","WAIT"].includes(i.op)){
      last.args[0]+=i.args[0]; continue;
    }
    if(last && last.op===i.op && (i.op==="LED_ON"||i.op==="LED_OFF")) continue;
    out.push({...i, args:[...i.args]});
  }
  return out;
}

function generate(ir){
  const emit = ({op,args})=>{
    switch(op){
      case "MOVE_FORWARD": return `    moveForward(${args[0]});`;
      case "MOVE_BACKWARD":return `    moveBackward(${args[0]});`;
      case "TURN_LEFT":    return `    turnLeft(${args[0]});`;
      case "TURN_RIGHT":   return `    turnRight(${args[0]});`;
      case "LED_ON":       return `    ledOn();`;
      case "LED_OFF":      return `    ledOff();`;
      case "LED_BLINK":    return `    ledBlink(${args[0]});`;
      case "WAIT":         return `    waitSeconds(${args[0]});`;
      case "STOP":         return `    stopRobot();`;
      case "IF":{
        const c = args[0].includes("OBSTACLE") ? "obstacleDetected()" : "sensorDetect()";
        return `    if (${c}) {\n    ${emit(args[1])}\n    }`;
      }
    }
  };
  return `// Auto-generated by AutoLang
#include <iostream>
int main() {
${ir.map(emit).join("\n")}
    return 0;
}`;
}

// ---------- UI ----------
const $ = id => document.getElementById(id);

function showPanel(name){
  document.querySelectorAll(".out").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  $(`out-${name}`).classList.add("active");
  document.querySelector(`.tab[data-tab="${name}"]`).classList.add("active");
}
document.querySelectorAll(".tab").forEach(tab =>
  tab.addEventListener("click", () => showPanel(tab.dataset.tab))
);

$("run").onclick = () => {
  const src = $("code").value;
  $("out-err").textContent = "";
  $("out-err").classList.remove("active");
  try {
    const toks = tokenize(src);
    const ast  = new Parser(toks).parse();
    semantic(ast);
    const ir   = optimize(lower(ast));

    $("out-tokens").textContent = toks.map(t=>`${t.type.padEnd(8)} ${String(t.value).padEnd(12)} line ${t.line}`).join("\n");
    $("out-ir").textContent     = ir.map(i=>`${i.op}(${i.args.join(", ")})`).join("\n");
    $("out-cpp").textContent    = generate(ir);
    showPanel("cpp");
  } catch(e) {
    $("out-err").textContent = "❌ " + e.message;
    document.querySelectorAll(".out").forEach(p => p.classList.remove("active"));
    $("out-err").classList.add("active");
  }
};

// Load example into editor
document.querySelectorAll(".try-ex").forEach(btn => {
  btn.addEventListener("click", e => {
    const pre = btn.closest(".card").querySelector("pre");
    $("code").value = pre.textContent.trim();
    window.scrollTo({ top: $("try").offsetTop - 40, behavior: "smooth" });
  });
});