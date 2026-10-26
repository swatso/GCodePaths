; Fork Lift Truck Moving Barrels
; ==============================

; ForkLift at Lorry to collect pallet
; X265 Y105 Z90

; Reverse and rotate
G1 X245 Y105 Z90 F80
G1 X245 Y105 Z180 F100

; Drive around Jet canopy
G1 X245 Y0 Z180 F100
G1 X245 Y0 Z270 F100
G1 X75 Y0 Z270 F100
G1 X75 Y0 Z180 F100
G1 X75 Y225 Z180 F100

; Forklift at Drop Off point next to Site Office
; X75 Y225 Z180






; Move the cherry picker across to the canopy
M106 S0 ; Detach Object
G4 S2 ; Pause
G1 X0.000 Y115.000 Z102.000 F5000
M106 S255 ; Attach Object
G4 S1 ; Pause
G1 X1.000 Y115.000 Z102.000 F200
G1 X67.000 Y129.000 Z102.000
G1 X99.000 Y109.000 Z54.000
G1 X129.000 Y61.000 Z31.000
G1 X135.000 Y25.000 Z2.000
G1 X135.000 Y24.000 Z2.000