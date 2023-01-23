# Author-Autodesk Inc
# Description-Import Ath4 curves from file and make it into printable parts

import adsk.core, adsk.fusion, math, traceback
import os.path, sys, configparser
from pathlib import Path

def getFaceWithX(faces, value):
    index = 0;

    for i in range(faces.count):
        myFace = faces.item(i)
        (_, x, _, _) = myFace.pointOnFace.getData()
        if (x == value):
            index = i
            break

    return faces.item(index)    


def getFaceWithY(faces, value):
    index = 0;

    for i in range(faces.count):
        myFace = faces.item(i)
        (_, _, y, _) = myFace.pointOnFace.getData()
        if (y == value):
            index = i
            break

    return faces.item(index)  


def getFaceWithZ(faces, value):
    index = 0;

    for i in range(faces.count):
        myFace = faces.item(i)
        (_, _, _, z) = myFace.pointOnFace.getData()
        if (z == value):
            index = i
            break

    return faces.item(index)  


def read_config(filename, unitsMgr):
    configFileName = Path(filename).with_suffix('.cfg')

    config = configparser.ConfigParser()
    config.read(configFileName)
    throatSettings = 'Throat'
    throatLength = unitsMgr.evaluateExpression(config[throatSettings]['length'], unitsMgr.defaultLengthUnits)
    throatMountingHoleDiameter = unitsMgr.evaluateExpression(config[throatSettings]['mountingHoleDiameter'], unitsMgr.defaultLengthUnits)
    throatSlotWidth = unitsMgr.evaluateExpression(config[throatSettings]['slotWidth'], unitsMgr.defaultLengthUnits)
    throatSlotDepth =  unitsMgr.evaluateExpression(config[throatSettings]['slotDepth'], unitsMgr.defaultLengthUnits)

    return throatLength, throatMountingHoleDiameter, throatSlotWidth, throatSlotDepth


def createMountingHoles(rootComp: adsk.fusion.Component, throatMountingHoleDiameter, extrudes: adsk.fusion.ExtrudeFeatures):
    bottomsketch: adsk.fusion.Sketch = rootComp.sketches.add(rootComp.yZConstructionPlane)
    bottomCircles = bottomsketch.sketchCurves.sketchCircles
    mountingHole1 = bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, 7.6/2, 0), throatMountingHoleDiameter/2)
    mountingHole2 = bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, -7.6/2, 0), throatMountingHoleDiameter/2)

    prof3 = bottomsketch.profiles.item(0)
    prof4 = bottomsketch.profiles.item(1)

    holeDistance = adsk.core.ValueInput.createByReal(1.0)
    extrudeHole1 = extrudes.addSimple(prof3, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudeHole2 = extrudes.addSimple(prof4, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)


def revolveProfileIntoWaveguide(sketch: adsk.fusion.Sketch, rootComp: adsk.fusion.Component):
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


def splitMouthIntoPetal(rootComp: adsk.fusion.Component, ext: adsk.fusion.ExtendFeature, splitBodyFeats):
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


def splitWaveguideIntoThroatAndMouth(fullWaveguide, rootComp: adsk.fusion.Component, throatLength):
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


def getRadiusOfLoop(loop: adsk.fusion.BRepLoop):
    brepEdges = loop.edges
    brepEdge = brepEdges.item(0)
    return brepEdge.length / (2.0*math.pi)


def determineMiddleRadiusOfThroatTop(throatTopFace: adsk.fusion.BRepFace):
    brepLoops = throatTopFace.loops
    radius1 = getRadiusOfLoop(brepLoops.item(0))
    radius2 = getRadiusOfLoop(brepLoops.item(1))
    middleRadius = (radius1 + radius2) / 2
    return middleRadius


def importAFP(filename, rootComp: adsk.fusion.Component, sketch):
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

        (throatLength, throatMountingHoleDiameter, throatSlotWidth, throatSlotDepth) = read_config(dlg.filename, unitsMgr)

        importAFP(dlg.filename, rootComp, sketch)

        (fullWaveguide, ext) = revolveProfileIntoWaveguide(sketch, rootComp)

        createMountingHoles(rootComp, throatMountingHoleDiameter, extrudes)

        (splitBodyFeats, offsetPlane) = splitWaveguideIntoThroatAndMouth(fullWaveguide, rootComp, throatLength)

        petal = splitMouthIntoPetal(rootComp, ext, splitBodyFeats)


        throat = ext.bodies.item(0)
        throat.name = 'Throat'
        faces: adsk.fusion.BRepFaces = throat.faces

        throatTopFace = getFaceWithX(faces, throatLength)
        comp: adsk.fusion.Component = throatTopFace.body.parentComponent
        throatTopSketch: adsk.fusion.Sketch = comp.sketches.add(throatTopFace)
        throatTopSketch.name = 'ThroatTop'

        # Draw some circles.
        mysketch: adsk.fusion.Sketch = rootComp.sketches.add(offsetPlane)

        circles = mysketch.sketchCurves.sketchCircles

        middleRadius = determineMiddleRadiusOfThroatTop(throatTopFace)

        circle1 = circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), middleRadius + throatSlotWidth/2)
        circle2 = circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), middleRadius - throatSlotWidth/2)

        prof2 = mysketch.profiles.item(0)  

        # Extrude Sample 1: A simple way of creating typical extrusions (extrusion that goes from the profile plane the specified distance).
        distance = adsk.core.ValueInput.createByReal(throatSlotDepth)
        minusDistance = adsk.core.ValueInput.createByReal(-throatSlotDepth)
        doubleDistance = adsk.core.ValueInput.createByReal(2*throatSlotDepth)
        extrude1 = extrudes.addSimple(prof2, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrude2 = extrudes.addSimple(prof2, minusDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extrude3 = extrudes.addSimple(prof2, doubleDistance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude3.bodies.item(0).name = 'RingConnector'
        ringConnector = extrude3.bodies.item(0)
        ringConnectorBottomFace = extrude3.startFaces.item(0)
        edgeCollection = adsk.core.ObjectCollection.create()
        edgeCollection.add(ringConnectorBottomFace.loops.item(0).edges.item(0))
        edgeCollection.add(ringConnectorBottomFace.loops.item(1).edges.item(0))

        
        # Create the FilletInput object.
        fillets = rootComp.features.filletFeatures
        filletInput = fillets.createInput()      
        filletInput.addConstantRadiusEdgeSet(edgeCollection, adsk.core.ValueInput.createByString('1 mm'), True)

        # Create the fillet.        
        fillet = fillets.add(filletInput)


        petalFaces: adsk.fusion.BRepFaces = petal.faces
        petalFace = getFaceWithY(petalFaces, 0.0)
        petalComp: adsk.fusion.Component = petalFace.body.parentComponent
        petalSketch: adsk.fusion.Sketch = petalComp.sketches.add(petalFace)
                
        # Create the offset.
        dirPoint = petalFace.pointOnFace
        connectedCurves = petalSketch.findConnectedCurves(petalSketch.sketchCurves.item(0))
        offsetCurves = petalSketch.offset(connectedCurves, dirPoint, -0.2)
        prof6 = petalSketch.profiles.item(0)

        extrudes = petalComp.features.extrudeFeatures
        petalConnectionDepth = adsk.core.ValueInput.createByReal(-0.3)
        connectionHeight = adsk.core.ValueInput.createByReal(2.0*0.3)
        extrudes.addSimple(prof6, petalConnectionDepth, adsk.fusion.FeatureOperations.CutFeatureOperation)
        connector = extrudes.addSimple(prof6, connectionHeight, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        connector.bodies.item(0).name = 'Connector'

        petalFace2 = getFaceWithZ(petalFaces, 0.0)
        petalComp2: adsk.fusion.Component = petalFace2.body.parentComponent
        petalSketch2: adsk.fusion.Sketch = petalComp2.sketches.add(petalFace2)
        dirPoint2 = petalFace2.pointOnFace
        connectedCurves2 = petalSketch2.findConnectedCurves(petalSketch2.sketchCurves.item(0))
        offsetCurves2 = petalSketch2.offset(connectedCurves2, dirPoint2, 0.2)
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

