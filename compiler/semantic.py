from .errors import SemanticError

class Semantic:
    def __init__(self, ast):
        self.ast = ast
        self.warnings = []

    def analyze(self):
        task_names = {t.name for t in self.ast.tasks}
        for t in self.ast.tasks:
            for s in t.body: 
                self._check(s, task_names)
                
        for s in self.ast.body: 
            self._check(s, task_names)
            
        return self.warnings

    def _check(self, n, tasks):
        if n.kind == "Move":
            if n.distance <= 0:
                raise SemanticError(f"Invalid movement distance: {n.distance}",
                                    line=n.line, hint="Distance must be positive.")
                                    
        elif n.kind == "Turn":
            if not (0 <= n.angle <= 360):
                raise SemanticError(f"Invalid angle: {n.angle}",
                                    line=n.line, hint="Angle must be 0..360.")
                                    
        elif n.kind == "Wait":
            if n.seconds < 0:
                raise SemanticError("WAIT seconds must be >= 0", line=n.line)
                
        elif n.kind == "Led" and n.mode == "BLINK":
            if n.times <= 0:
                raise SemanticError("LED BLINK times must be > 0", line=n.line)
                
        elif n.kind == "Run":
            if n.name not in tasks:
                raise SemanticError(f"Undefined task '{n.name}'", line=n.line)
                
        # --- NEW: The missing Servo rule ---
        elif n.kind == "Servo":
            if not (0 <= n.angle <= 180):
                raise SemanticError(f"Invalid servo angle: {n.angle}",
                                    line=n.line, hint="Servo angle must be between 0 and 180.")
                                    
        elif n.kind == "If":
            self._check(n.action, tasks)
            
        # --- NEW: Ensure we check inside LOOPS ---
        elif n.kind == "Loop":
            for stmt in n.body:
                self._check(stmt, tasks)