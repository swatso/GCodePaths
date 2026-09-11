; Workmen with board - move inside shedA
; First Open the door on ShedA (nearest the front of diorama)
M106 S0
G4 S1
G1 X41 Y31 Z194 F750
M106 S255
G4 S1
G1 X41 Y31 Z73 F50

; Now fetch the workmen from home and move them into the shed
M106 S0
G4 S1
G1	X0.000	Y0.000	Z90.000 F1000
M106 S255
G4 S1
G1	X113 Y0 Z90
G1	X113 Y47 Z90
G1	X0 Y47 Z90

; Now Close the door on ShedA (the one nearest the front of the diorama)
M106 S0
G4 S1
G1 X41 Y31 Z73 F750
M106 S255
G4 S1
G1 X41 Y31 Z194 F50