; Fork Lift Truck Moving Barrels
; ==============================

M106 S0 ; Detach Object
G4 S2 ; Pause
G1 X265 Y105 Z90 F1000

; ForkLift at Lorry to collect pallet
; X265 Y105 Z90

M106 S255 ; Attach Object
G4 S2

; Reverse and rotate
G1 X245 Y105 Z90 F80
G1 X245 Y105 Z180 F100

; Drive around Jet canopy
G1 X245 Y0 Z180 F300
G1 X245 Y0 Z270 F300
G1 X75 Y0 Z270 F300
G1 X75 Y0 Z180 F300
G1 X75 Y200 Z180 F500
G1 X75 Y215 Z180 F200
G1 X75 Y225 Z180 F80

; Forklift at Drop Off point next to Site Office
; X75 Y225 Z180


