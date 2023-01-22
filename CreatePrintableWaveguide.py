# Author-Autodesk Inc
# Description-Import Ath4 curves from file and make it into printable parts

import adsk.core, adsk.fusion, math, traceback
import os.path, sys, configparser
from pathlib import Path


def read_config(filename, unitsMgr):
    configFileName = Path(filename).with_suffix('.cfg')

    config = configparser.ConfigParser()
    config.read(configFileName)
    throatSettings = 'Throat'
    throatLength = unitsMgr.evaluateExpression(config[throatSettings]['length'], unitsMgr.defaultLengthUnits)

    throatMountingHoleDiameter = unitsMgr.evaluateExpression(config[throatSettings]['mountingHoleDiameter'], unitsMgr.defaultLengthUnits)

    return throatLength, throatMountingHoleDiameter


def createMountingHoles(rootComp, throatMountingHoleDiameter, extrudes):
    bottomsketch: adsk.fusion.Sketch = rootComp.sketches.add(rootComp.yZConstructionPlane)
    bottomCircles = bottomsketch.sketchCurves.sketchCircles
    mountingHole1 = bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, 7.6/2, 0), throatMountingHoleDiameter/2)
    mountingHole2 = bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, -7.6/2, 0), throatMountingHoleDiameter/2)

    prof3 = bottomsketch.profiles.item(0)
    prof4 = bottomsketch.profiles.item(1)

    holeDistance = adsk.core.ValueInput.createByReal(1.0)
    extrudeHole1 = extrudes.addSimple(prof3, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudeHole2 = extrudes.addSimple(prof4, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)


def revolveProfileIntoWaveguide(sketch, rootComp):
    # Draw a line to use as the axis of revolution.
    lines2 = sketch.sketchCurves.sketchLines
    axisLine = lines2.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(1, 0, 0)) # X axis

    # Get the profile defined by the ath waveguide profile.
    prof = sketch.profiles.item(0)

    # Create an revolution input to be able to define the input needed for a revolution
    # while specifying the profile and that a new component is to be created
    revolves = rootComp.features.revolveFeatures
    revInput = revolves.createInput(prof, axisLine, adsk.fusion.FeatureOperations.NewComponentFeatureOperation)

    # Define that the extent is an angle of 360 degrees
    angle = adsk.core.ValueInput.createByString("360.0 deg")
    revInput.setAngleExtent(False, angle)

    # Create the full waveguide.
    ext = revolves.add(revInput)

    # Get the waveguide created by the revolution
    fullWaveguide = ext.bodies.item(0)

    return fullWaveguide, ext


def splitMouthIntoPetal(rootComp, ext, splitBodyFeats):
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

    return petal


def splitWaveguideIntoThroatAndMouth(fullWaveguide, rootComp, throatLength):
    # Create a construction plane by offsetting the end face
    # This is where the waveguide will be split into he throat and the mouth (petals)
    planes = rootComp.constructionPlanes
    planeInput = planes.createInput()
    offsetVal = adsk.core.ValueInput.createByReal(throatLength)
    planeInput.setByOffset(rootComp.yZConstructionPlane, offsetVal)
    offsetPlane = planes.add(planeInput)
    
    # Create SplitBodyFeatureInput
    splitBodyFeats = rootComp.features.splitBodyFeatures
    splitBodyInput = splitBodyFeats.createInput(fullWaveguide, offsetPlane, True)
    
    # Create split body feature
    splitBodyFeats.add(splitBodyInput)

    return splitBodyFeats, offsetPlane


def importAFP(filename, rootComp, sketch):
    f = open(filename, 'r')
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

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design: adsk.fusion.Design = app.activeProduct
        unitsMgr = design.unitsManager
        if not design:
            ui.messageBox('No active Fusion design', 'Ath Profile Import')
            return
        rootComp = design.rootComponent
        
        dlg = ui.createFileDialog()
        dlg.title = 'Open Ath Profile'
        dlg.filter = 'Ath Profile Definition (*.afp);;All Files (*.*)'
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return

        sketch: adsk.fusion.Sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        # Get extrude features
        extrudes = rootComp.features.extrudeFeatures

        (throatLength, throatMountingHoleDiameter) = read_config(dlg.filename, unitsMgr)

        importAFP(dlg.filename, rootComp, sketch)

        (fullWaveguide, ext) = revolveProfileIntoWaveguide(sketch, rootComp)

        createMountingHoles(rootComp, throatMountingHoleDiameter, extrudes)

        (splitBodyFeats, offsetPlane) = splitWaveguideIntoThroatAndMouth(fullWaveguide, rootComp, throatLength)

        petal = splitMouthIntoPetal(rootComp, ext, splitBodyFeats)


        throat = ext.bodies.item(0)
        throat.name = 'Throat'
        faces: adsk.fusion.BRepFaces = throat.faces

        throatTopFace = faces.item(7)
        comp: adsk.fusion.Component = throatTopFace.body.parentComponent
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

        prof2 = mysketch.profiles.item(0)  

        # Extrude Sample 1: A simple way of creating typical extrusions (extrusion that goes from the profile plane the specified distance).
        distance = adsk.core.ValueInput.createByString('2 mm')
        minusDistance = adsk.core.ValueInput.createByString('-2 mm')
        doubleDistance = adsk.core.ValueInput.createByString('4 mm')
        extrude1 = extrudes.addSimple(prof2, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrude2 = extrudes.addSimple(prof2, minusDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrude3 = extrudes.addSimple(prof2, doubleDistance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude3.bodies.item(0).name = 'RingConnector'


        petalFaces: adsk.fusion.BRepFaces = petal.faces
        petalFace = petalFaces.item(3)
        petalComp: adsk.fusion.Component = petalFace.body.parentComponent
        petalSketch: adsk.fusion.Sketch = petalComp.sketches.add(petalFace)
                
        # Create the offset.
        dirPoint = adsk.core.Point3D.create(0, .5, 0)
        connectedCurves = petalSketch.findConnectedCurves(petalSketch.sketchCurves.item(0))
        offsetCurves = petalSketch.offset(connectedCurves, dirPoint, -1.0)
        prof6 = petalSketch.profiles.item(0)

        extrudes = petalComp.features.extrudeFeatures
        petalConnectionDepth = adsk.core.ValueInput.createByReal(-0.3)
        connectionHeight = adsk.core.ValueInput.createByReal(2.0*0.3)
        extrudes.addSimple(prof6, petalConnectionDepth, adsk.fusion.FeatureOperations.CutFeatureOperation)
        connector = extrudes.addSimple(prof6, connectionHeight, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        connector.bodies.item(0).name = 'Connector'


        # loop over faces and get a point on that plane and check whether one of the axis is nonzero
        #rootComp.findBRepUsingPoint(adsk.core.Point3D(0,0,0), adsk.fusion.BRepEntityTypes.BRepFaceEntityType, 0.1, visibleEntitiesOnly=True)
        petalFace2 = petalFaces.item(16)
        petalComp2: adsk.fusion.Component = petalFace2.body.parentComponent
        petalSketch2: adsk.fusion.Sketch = petalComp2.sketches.add(petalFace2)
        dirPoint2 = adsk.core.Point3D.create(0, 0, -0.5)
        connectedCurves2 = petalSketch2.findConnectedCurves(petalSketch2.sketchCurves.item(1))
        offsetCurves2 = petalSketch2.offset(connectedCurves2, dirPoint2, -1.5)
        prof7 = petalSketch2.profiles.item(1)
        extrudes2 = petalComp2.features.extrudeFeatures
        extrudes2.addSimple(prof7, petalConnectionDepth, adsk.fusion.FeatureOperations.CutFeatureOperation)


        # kinda works, but other stuff needs to be done first:

        # # create a single exportManager instance
        exportMgr = design.exportManager
        
        scriptDir = os.path.dirname(os.path.abspath(dlg.filename))
        
        # # export the occurrence one by one in the root component to a specified file
        # allOccu = rootComp.allOccurrences
        # for occ in allOccu:
        #     if occ.isVisible:
        #         fileName = scriptDir + "/" + occ.component.name
                
        #         # create stl exportOptions
        #         stlExportOptions = exportMgr.createSTLExportOptions(occ, fileName)
        #         stlExportOptions.sendToPrintUtility = False
                
        #         exportMgr.execute(stlExportOptions)

        # export the body one by one in the design to a specified file
        # allBodies = rootComp.bRepBodies
        # for body in allBodies:
        #     if body.isVisible:
        #         fileName = scriptDir + "/" + body.parentComponent.name + '-' + body.name
                
        #         # create stl exportOptions
        #         stlExportOptions = exportMgr.createSTLExportOptions(body, fileName)
        #         stlExportOptions.sendToPrintUtility = False
                
        #         exportMgr.execute(stlExportOptions)

            
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

