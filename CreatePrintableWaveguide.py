# Author-Autodesk Inc
# Description-Import Ath4 curves from file and make it into printable parts

import adsk.core, adsk.fusion, math, traceback

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
        offsetVal = adsk.core.ValueInput.createByString('8 cm')
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
        circles = throatTopSketch.sketchCurves.sketchCircles
        circle1 = circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), radius - 0.5)
        circle2 = circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), radius - 0.8)

        # Get extrude features
        extrudes = rootComp.features.extrudeFeatures

        prof2 = throatTopSketch.profiles.item(0)


        # Extrude Sample 1: A simple way of creating typical extrusions (extrusion that goes from the profile plane the specified distance).
        # Define a distance extent of 5 cm
        distance = adsk.core.ValueInput.createByReal(0.2)
        # TODO should be another prof(ile)
        extrude1 = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrude2 = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.JoinFeatureOperation)



            
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

