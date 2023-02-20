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

class Throat:
    length = 0

class MountingHoles:    
    diameter = 0
    holeDiameter = 0

class ThroatMouthConnector:    
    slotWidth = 0
    slotDepth = 0
    connectorWidth = 0
    connectorHeight = 0
    hasFillet = False
    filletSize = 0

class PetalConnector:
    petalThickness = 0
    slotWidth = 0
    slotDepth = 0
    connectorWidth = 0
    connectorHeight = 0
    hasFillet = False
    filletSize = 0


class Petal:
    roundBack = False

def readQuantity(config, settingsName, variableName, unitsMgr):
     return unitsMgr.evaluateExpression(config[settingsName][variableName], unitsMgr.defaultLengthUnits)
    

def read_config(filename, unitsMgr):
    configFileName = Path(filename).with_suffix('.cfg')

    config = configparser.ConfigParser()
    config.read(configFileName)

    throatSettingsName = 'Throat'
    throatSettings = Throat()
    throatSettings.length = readQuantity(config, throatSettingsName, 'length', unitsMgr)

    mountingHoleSettingsName = 'MountingHoles'
    mountingHoleSettings = MountingHoles()
    mountingHoleSettings.holeDiameter = readQuantity(config, mountingHoleSettingsName, 'holeDiameter', unitsMgr)
    mountingHoleSettings.diameter = readQuantity(config, mountingHoleSettingsName, 'diameter', unitsMgr)

    petalSettingsName = 'Petal'
    petalSettings = Petal()
    petalSettings.roundBack = config[petalSettingsName]['roundBack'] == 'True'

    throatMouthConnectorSettingsName = 'ThroatMouthConnector'
    throatMouthConnectorSettings = ThroatMouthConnector()
    throatMouthConnectorSettings.slotWidth = readQuantity(config, throatMouthConnectorSettingsName, 'slotWidth', unitsMgr)
    throatMouthConnectorSettings.slotDepth = readQuantity(config, throatMouthConnectorSettingsName, 'slotDepth', unitsMgr)
    throatMouthConnectorSettings.connectorWidth = readQuantity(config, throatMouthConnectorSettingsName, 'connectorWidth', unitsMgr)
    throatMouthConnectorSettings.connectorHeight = readQuantity(config, throatMouthConnectorSettingsName, 'connectorHeight', unitsMgr)
    throatMouthConnectorSettings.hasFillet = True
    throatMouthConnectorSettings.filletSize = readQuantity(config, throatMouthConnectorSettingsName, 'filletSize', unitsMgr)

    petalConnectorSettingsName = 'PetalConnector'
    petalConnectorSettings = PetalConnector()
    petalConnectorSettings.petalThickness = readQuantity(config, petalConnectorSettingsName, 'petalThickness', unitsMgr)
    petalConnectorSettings.slotWidth = readQuantity(config, petalConnectorSettingsName, 'slotWidth', unitsMgr)
    petalConnectorSettings.slotDepth = readQuantity(config, petalConnectorSettingsName, 'slotDepth', unitsMgr)
    petalConnectorSettings.connectorWidth = readQuantity(config, petalConnectorSettingsName, 'connectorWidth', unitsMgr)
    petalConnectorSettings.connectorHeight = readQuantity(config, petalConnectorSettingsName, 'connectorHeight', unitsMgr)
    petalConnectorSettings.hasFillet = True
    petalConnectorSettings.filletSize = readQuantity(config, petalConnectorSettingsName, 'filletSize', unitsMgr)

    return throatSettings, mountingHoleSettings, petalSettings, throatMouthConnectorSettings, petalConnectorSettings


def createMountingHoles(rootComp: adsk.fusion.Component, mountingHoleSettings, extrudes: adsk.fusion.ExtrudeFeatures):
    bottomsketch: adsk.fusion.Sketch = rootComp.sketches.add(rootComp.yZConstructionPlane)
    bottomCircles = bottomsketch.sketchCurves.sketchCircles
    bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, mountingHoleSettings.diameter/2, 0), mountingHoleSettings.holeDiameter/2)
    bottomCircles.addByCenterRadius(adsk.core.Point3D.create(0, -mountingHoleSettings.diameter/2, 0), mountingHoleSettings.holeDiameter/2)

    prof3 = bottomsketch.profiles.item(0)
    prof4 = bottomsketch.profiles.item(1)

    holeDistance = adsk.core.ValueInput.createByReal(1.0) # TODO should go through flange 
    hole = extrudes.addSimple(prof3, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudes.addSimple(prof4, holeDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # # Get the body created by extrusion
    # # body = hole.bodies.item(0)
    
    # # Create input entities for circular pattern
    # inputEntities = adsk.core.ObjectCollection.create()
    # inputEntities.add(hole)
    
    # # Get X axis for circular pattern
    # xAxis = rootComp.xConstructionAxis
    
    # # Create the input for circular pattern
    # circularFeats = rootComp.features.circularPatternFeatures
    # circularFeatInput = circularFeats.createInput(inputEntities, xAxis)
    
    # # Set the quantity of the elements
    # circularFeatInput.quantity = adsk.core.ValueInput.createByReal(5)
    
    # # Set the angle of the circular pattern
    # circularFeatInput.totalAngle = adsk.core.ValueInput.createByString('180 deg')
    
    # # Set symmetry of the circular pattern
    # circularFeatInput.isSymmetric = False
    
    # # Create the circular pattern
    # circularFeats.add(circularFeatInput)


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


def importAFP(filename, rootComp: adsk.fusion.Component, sketch: adsk.fusion.Sketch, roundBack):
    f = open(filename, 'r')
    lines = sketch.sketchCurves.sketchLines
    circles = sketch.sketchCurves.sketchCircles
    arcs = sketch.sketchCurves.sketchArcs
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
            if ((items[1] == '61') & (roundBack)):
                # this adds a half torus back to the waveguide adge
                one = points[items[1]]
                two = points[items[2]]
                three = adsk.core.Point3D.create((one.x+two.x)/2, (one.y+two.y)/2, (one.z+two.z)/2)
                arcs.addByCenterStartSweep(three, one, math.pi)
            else:
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

def generatePetalConnection(petal: adsk.fusion.BRepBody, petalConnectionSettings: PetalConnector):
    petalFaces: adsk.fusion.BRepFaces = petal.faces
    petalFace = getFaceWithY(petalFaces, 0.0)
    petalComp: adsk.fusion.Component = petalFace.body.parentComponent
    petalSketch: adsk.fusion.Sketch = petalComp.sketches.add(petalFace)

    edgeThickness = (petalConnectionSettings.petalThickness - petalConnectionSettings.slotWidth)/2
    edgeThickness2 = (petalConnectionSettings.petalThickness - petalConnectionSettings.connectorWidth)/2
            
    # Create the offset.
    dirPoint = petalFace.pointOnFace
    connectedCurves = petalSketch.findConnectedCurves(petalSketch.sketchCurves.item(0))
    petalSketch.offset(connectedCurves, dirPoint, -edgeThickness2)
    prof6 = petalSketch.profiles.item(0)

    extrudes = petalComp.features.extrudeFeatures
    petalConnectionDepth = adsk.core.ValueInput.createByReal(-petalConnectionSettings.slotDepth)
    connectionHeight = adsk.core.ValueInput.createByReal(petalConnectionSettings.connectorHeight)

    extInput: adsk.fusion.ExtrudeFeatureInput = extrudes.createInput(prof6, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # Create the offset.
    petalSketch.offset(connectedCurves, dirPoint, -edgeThickness)
    prof6b = prof6 #petalSketch.profiles.item(2)
   
    extInput.setSymmetricExtent(connectionHeight, True)

    extrudes.addSimple(prof6b, petalConnectionDepth, adsk.fusion.FeatureOperations.CutFeatureOperation)

    connector = extrudes.add(extInput)
    connector.bodies.item(0).name = 'PetalConnector'

    petalFace2 = getFaceWithZ(petalFaces, 0.0)
    petalComp2: adsk.fusion.Component = petalFace2.body.parentComponent
    petalSketch2: adsk.fusion.Sketch = petalComp2.sketches.add(petalFace2)
    dirPoint2 = petalFace2.pointOnFace
    connectedCurves2 = petalSketch2.findConnectedCurves(petalSketch2.sketchCurves.item(0))
    petalSketch2.offset(connectedCurves2, dirPoint2, edgeThickness)
    prof7 = petalSketch2.profiles.item(1)
    extrudes2 = petalComp2.features.extrudeFeatures
    extrudes2.addSimple(prof7, petalConnectionDepth, adsk.fusion.FeatureOperations.CutFeatureOperation)


def createThroatMouthConnector(throat: adsk.fusion.BRepBody, rootComp: adsk.fusion.Component, offsetPlane, throatMouthConnectorSettings: ThroatMouthConnector, throatLength):
    extrudes = rootComp.features.extrudeFeatures

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

    circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), middleRadius + throatMouthConnectorSettings.slotWidth/2)
    circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), middleRadius - throatMouthConnectorSettings.slotWidth/2)

    prof2 = mysketch.profiles.item(0)  

    # Extrude Sample 1: A simple way of creating typical extrusions (extrusion that goes from the profile plane the specified distance).
    distance = adsk.core.ValueInput.createByReal(throatMouthConnectorSettings.slotDepth)
    minusDistance = adsk.core.ValueInput.createByReal(-throatMouthConnectorSettings.slotDepth)
    connectorHeight = adsk.core.ValueInput.createByReal(throatMouthConnectorSettings.connectorHeight)
    extrudes.addSimple(prof2, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudes.addSimple(prof2, minusDistance, adsk.fusion.FeatureOperations.CutFeatureOperation)

    circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), middleRadius + throatMouthConnectorSettings.connectorWidth/2)
    circles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), middleRadius - throatMouthConnectorSettings.connectorWidth/2)

    prof3 = mysketch.profiles.item(2)  

    extInput: adsk.fusion.ExtrudeFeatureInput = extrudes.createInput(prof3, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
   
    extInput.setSymmetricExtent(connectorHeight, True)
    extrude3 = extrudes.add(extInput)
    extrude3.bodies.item(0).name = 'RingConnector'   

    ringConnectorBottomFace = extrude3.startFaces.item(0)
    edgeCollection = adsk.core.ObjectCollection.create()
    edgeCollection.add(ringConnectorBottomFace.loops.item(0).edges.item(0))
    edgeCollection.add(ringConnectorBottomFace.loops.item(1).edges.item(0))
    
    # Create the FilletInput object.
    fillets = rootComp.features.filletFeatures
    filletInput = fillets.createInput()      
    filletInput.addConstantRadiusEdgeSet(edgeCollection, adsk.core.ValueInput.createByReal(throatMouthConnectorSettings.filletSize), True)

    # Create the fillet.        
    fillets.add(filletInput) 
    

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

        (throatSettings, mountingHoleSettings, petalSettings, throatMouthConnectorSettings, petalConnectorSettings) = read_config(dlg.filename, unitsMgr)

        importAFP(dlg.filename, rootComp, sketch, petalSettings.roundBack)

        (fullWaveguide, ext) = revolveProfileIntoWaveguide(sketch, rootComp)

        createMountingHoles(rootComp, mountingHoleSettings, extrudes)

        (splitBodyFeats, offsetPlane) = splitWaveguideIntoThroatAndMouth(fullWaveguide, rootComp, throatSettings.length)

        petal = splitMouthIntoPetal(rootComp, ext, splitBodyFeats)

        throat = ext.bodies.item(0)
        createThroatMouthConnector(throat, rootComp, offsetPlane, throatMouthConnectorSettings, throatSettings.length)

        generatePetalConnection(petal, petalConnectorSettings)


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

