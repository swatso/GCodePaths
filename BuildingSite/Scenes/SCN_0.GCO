; Tarmac Laying Scene
; ===================

; Move Tarmac Layer to starting position
M106 S0 ; Detach Object
G4 S1 ; Pause
G1 X186.000 Y115.000 Z90.000 F5000
M106 S255 ; Attach Object
G4 S1 ; Pause
G1 X255.000 Y115.000 Z90.000 F500
G1 X255.000 Y115.000 Z90.000
G1 X255.000 Y115.000 Z0.000
G1 X255.000 Y215.000 Z0.000

; Forman leaves office and walks to Tarmac Layer
M106 S0 ; Detach Object
G4 S1 ; Pause
G1 X0 Y225 Z0 F5000
M106 S255 ; Attach Object
G4 S1 ; Pause
G1 X18 Y225 Z0 F200
G1 X18 Y189 Z0
G1 X18 Y189 Z90 F1000
G1 X140 Y211 Z90 F200
G1 X220 Y206 Z90
G1 X220 Y208 Z30

; Pause while he gives instructions then start
M106 S0 ; Detach Object
G4 S2 ; Pause
G1 X265.000 Y215.000 Z0.000
M106 S255 ; Attach Object
G4 S5 ; Pause
G1 X265.000 Y25.000 Z0.000 F200   ; Forward strip

; Forman turns back
M106 S0 ; Detach Object
G4 S1 ; Pause
G1 X220 Y208 Z30 F5000
M106 S255 ; Attach Object
G4 S1
G1 X220 Y225 Z30 F200
G1 X220 Y225 Z270 F2000    ; face the other way
G1 X220 Y208 Z270 F200
G1 X164 Y208 Z270 F200

; Return from first strip
M106 S0 ; Detach Object
G4 S2 ; Pause
G1 X265.000 Y25.000 Z0.000 F5000
M106 S255 ; Attach Object
G4 S1
G1 X245.000 Y215.000 Z0.000 F300  ; Reverse
G4 S5
G1 X245.000 Y25.000 Z0.000 F200   ; Forward strip
G4 S4

; Forman returns to office
M106 S0 ; Detach Object
G4 S1 ; Pause
G1 X164 Y208 Z270 F5000
M106 S255 ; Attach Object
G4 S1
G1 X121 Y202 Z280 F200
G1 X18 Y189 Z250
G1 X18 Y189 Z0 F2000
G1 X18 Y225 Z0 F200
G1 X0 Y225 Z0

; Back to the TarMac Layer
M106 S0 ; Detach Object
G4 S2 ; Pause
G1 X245.000 Y25.000 Z0.000 F5000
M106 S255 ; Attach Object
G4 S1
G1 X255.000 Y215.000 Z0.000 F300  ; Reverse
G4 S5
; Move Tarmac Layer back to Start Of Day position
G1 X256.000 Y115.000 Z0.000
G1 X255.000 Y115.000 Z90.000
G1 X186.000 Y115.000 Z90.000 F500
