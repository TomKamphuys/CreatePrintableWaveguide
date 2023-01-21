# Author-Autodesk Inc
# Description-Import Ath4 curves from file and make it into printable parts

import adsk.core, adsk.fusion, math, traceback
import os.path, sys, configparser
from pathlib import Path


def read_config(dlg):
    configFileName = Path(dlg.filename).with_suffix('.cfg')

    config = configparser.ConfigParser()
    config.read(configFileName)
    throatSettings = 'Throat'
    throatLength = float(config[throatSettings]['Length'])
    throatMountingHoleDiameter = float(config[throatSettings]['MountingHoleDiameter'])

    return throatLength, throatMountingHoleDiameter


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design: adsk.fusion.Design = app.activeProduct
        if not design:
            ui.messageBox('No active Fusion design', 'Ath Profile Import')
            return
        rootComp = design.rootComponent
        
        dlg = ui.createFileDialog()
        dlg.title = 'Open Ath Profile'
        dlg.filter = 'Ath Profile Definition (*.afp);;All Files (*.*)'
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return

        f = open(dlg.filename, 'r')
        sketch: adsk.fusion.Sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        lines = sketch.sketchCurves.sketchLines
        points = {}
        
        line = f.readline().rstrip()
        while line:
            if len(line) < 3 or line[0] == '#':
                line = f.readline().rstrip()
                continue
            items = line.split(' ')
            if line[0] == 'P' and len(items) >= 4:
                points[items[1]] = adsk.core.Point3D.create(
                    0.1*float(items[2]), 0.1*float(items[3]), 0.0
                )
            elif line[0] == 'L' and len(items) >= 3:
                lines.addByTwoPoints(points[items[1]], points[items[2]])
            
            elif line[0] == 'S' and len(items) >= 3:
                splinePoints = adsk.core.ObjectCollection.create()
                for k in range(int(items[1]), int(items[2]) + 1):
                    splinePoints.add(points[str(k)])
                sketch.sketchCurves.sketchFittedSplines.add(splinePoints)
            
            elif line[0] == 'U':
                splinePoints = adsk.core.ObjectCollection.create()
                for k in items[1:]:
                    splinePoints.add(points[k])
                sketch.sketchCurves.sketchFittedSplines.add(splinePoints)
                
            line = f.readline().rstrip()
        f.close()

        (throatLength, throatMountingHoleDiameter) = read_config(dlg)

        # Draw a line to use as the axis of revolution.
        lines2 = sketch.sketchCurves.sketchLines
        axisLine = lines2.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(1, 0, 0)) # X axis

        # Get the profile defined by the ath waveguide profile.
        prof = sketch.profiles.item(0)

        # Create an revolution input to be able to define the input needed for a revolution
        # while specifying the profile and that a new component is to be created
        revolves = rootComp.features.revolveFeatures
        revInput = revolves.createInput(prof, axisLine, adsk.fusion.FeatureOperations.NewComponentFeatureOperation)

        # Define that the extent is an angle of pi to get half of a torus.
        angle = adsk.core.ValueInput.createByReal(2*math.pi)
        revInput.setAngleExtent(False, angle)

        # Create the extrusion.
        ext = revolves.add(revInput)

        # Get the body created by the extrusion
        body = ext.bodies.item(0)

        # Create a construction plane by offsetting the end face
        planes = rootComp.constructionPlanes
        planeInput = planes.createInput()
        offsetVal = adsk.core.ValueInput.createByReal(throatLength)
        planeInput.setByOffset(rootComp.yZConstructionPlane, offsetVal)
        offsetPlane = planes.add(planeInput)
        
        # Create SplitBodyFeatureInput
        splitBodyFeats = rootComp.features.splitBodyFeatures
        splitBodyInput = splitBodyFeats.createInput(body, offsetPlane, True)
        
        # Create split body feature
        splitBodyFeats.add(splitBodyInput)

        # split petal
        mouth = ext.bodies.item(1)
        splitBodyInput2 = splitBodyFeats.createInput(mouth, rootComp.xZConstructionPlane, True)
        splitBodyFeats.add(splitBodyInput2)

        halfMouth = ext.bodies.item(2)
        splitBodyInput3 = splitBodyFeats.createInput(halfMouth, rootComp.xYConstructionPlane, True)
        splitBodyFeats.add(splitBodyInput3) 

        petal = ext.bodies.item(2)
        petal.name = 'Petal'       

        ext.bodies.item(3).isVisible = False
        ext.bodies.item(1).isVisible = False

        throat = ext.bodies.item(0)
        throat.name = 'Throat'
        faces: adsk.fusion.BRepFaces = throat.faces

        throatBottomFace = faces.item(0)
        comp: adsk.fusion.Component = throatBottomFace.body.parentComponent
        throatBottomSketch: adsk.fusion.Sketch = comp.sketches.add(throatBottomFace)
        throatBottomSketch.name = 'ThroatBottom'

        throatTopFace = faces.item(5)
        # comp: adsk.fusion.Component = throatBottomFace.body.parentComponent
        throatTopSketch: adsk.fusion.Sketch = comp.sketches.add(throatTopFace)
        throatTopSketch.name = 'ThroatTop'

        brepLoops = throatTopFace.loops
        outerLoop = brepLoops.item(0)
        if not outerLoop.isOuter:
            outerLoop = brepLoops.item(1)
        brepEdges = outerLoop.edges
        brepEdge = brepEdges.item(0)
        radius = brepEdge.length / (2.0*math.pi)

        # Draw some circles.
        mysketch: adsk.fusion.Sketch = rootComp.sketches.add(offsetPlane)

        circles = mysketch.sketchCurves.sketchCircles

        circle1 = circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), radius - 0.5)
        circle2 = circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), radius - 0.8)

        # Get extrude features
        extrudes = rootComp.features.extrudeFeatures

        prof2 = mysketch.profiles.item(0)  

        # Extrude Sample 1: A simple way of creating typical extrusions (extrusion that goes from the profile plane the specified distance).
        # Define a distance extent of 5 cm
        distance = adsk.core.ValueInput.createByReal(0.2)
        extrude1 = extrudes.addSimple(prof2, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrude2 = extrudes.addSimple(prof2, distance, adsk.fusion.FeatureOperations.JoinFeatureOperation)


        bottomsketch: adsk.fusion.Sketch = rootComp.sketches.add(rootComp.yZConstructionPlane)
        bottomCircles = bottomsketch.sketchCurves.sketchCircles
        # mountingHoleHelper = bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), 7.6/2)
        # mountingHoleHelper.isConstruction = True
        mountingHole1 = bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, 7.6/2, 0), throatMountingHoleDiameter/2)
        mountingHole2 = bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, -7.6/2, 0), throatMountingHoleDiameter/2)

        prof3 = bottomsketch.profiles.item(0)
        prof4 = bottomsketch.profiles.item(1)

        holeDistance = adsk.core.ValueInput.createByReal(1.0)
        extrudeHole1 = extrudes.addSimple(prof3, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrudeHole2 = extrudes.addSimple(prof4, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)


        # petalFaces: adsk.fusion.BRepFaces = petal.faces
        # petalFace0 = petalFaces.item(0)
        # petalComp: adsk.fusion.Component = petalFace0.body.parentComponent
        # petalSketch: adsk.fusion.Sketch = petalComp.sketches.add(petalFace0)
        # petalSketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), 0.5)



        # Lot's of stuff to do...





        # kinda works, but other stuff needs to be done first:

        # # create a single exportManager instance
        exportMgr = design.exportManager
        
        # scriptDir = os.path.dirname(os.path.abspath(dlg.filename))
        
        # # export the occurrence one by one in the root component to a specified file
        # allOccu = rootComp.allOccurrences
        # for occ in allOccu:
        #     fileName = scriptDir + "/" + occ.component.name
            
        #     # create stl exportOptions
        #     stlExportOptions = exportMgr.createSTLExportOptions(occ, fileName)
        #     stlExportOptions.sendToPrintUtility = False
            
        #     exportMgr.execute(stlExportOptions)

        # # export the body one by one in the design to a specified file
        # allBodies = rootComp.bRepBodies
        # for body in allBodies:
        #     fileName = scriptDir + "/" + body.parentComponent.name + '-' + body.name
            
        #     # create stl exportOptions
        #     stlExportOptions = exportMgr.createSTLExportOptions(body, fileName)
        #     stlExportOptions.sendToPrintUtility = False
            
        #     exportMgr.execute(stlExportOptions)

            
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

