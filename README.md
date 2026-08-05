This repository contains paths for objects in a diorama controlled by a Marlin based CNC controller
The paths are in GCODE and predominately use the G1 command to set X,Y and Z coordinates and feedrate (transit speed)
In the diorama, Z refers to the retation (bearing) of the object under control in degrees
The hardware moves a puck under the surface of the diorama, it carries 2 rare earth magnets 20mm apart which
can be raised / lowered using the M106 command (M106 S0  to lower, M106 S255 to raise) 
use the delay command (G4 S2) to allow time for the servos to complete raieing/lowering the magnets

The files are typically stored on an SD card and read directly by the Marlin Controller through GCODE command
sequences sent to it by the higher level Diorama Controller. Marlin uses the classic 8.3 File naming rules, but
allows Directories. So the convension adopted here is:-

root--+
      +--Object0
            +--Path0
            +--Path1
            +--...
      +--Object1
            +--Path0
            +--...

Essentially there is no limit to the number of objects, but currently we are working with 16
Every Object needs a Path0 file which should describe a path from 0,0,90  to the start of day position of the Object

+
