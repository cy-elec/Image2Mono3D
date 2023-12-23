import adsk.core, adsk.fusion
import os, traceback
from ...lib.PIL import Image
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface
design = adsk.fusion.Design.cast(app.activeProduct)

# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_image2mono3d'
CMD_NAME = 'Image to Monochrome 3D'
CMD_Description = 'Converts a user provided image to a monochrome 3D mesh.'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidModifyPanel'
COMMAND_BESIDE_ID = 'FusionShellBodyCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
RESOURCES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []
loadedImage = None

# Executed when add-in is run.
def start():
	# Create a command Definition.
	cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, RESOURCES_FOLDER+"/command")

	# Define an event handler for the command created event. It will be called when the button is clicked.
	futil.add_handler(cmd_def.commandCreated, command_created)

	# ******** Add a button into the UI so the user can run the command. ********
	# Get the target workspace the button will be created in.
	workspace = ui.workspaces.itemById(WORKSPACE_ID)

	# Get the panel the button will be created in.
	panel = workspace.toolbarPanels.itemById(PANEL_ID)

	# Create the button command control in the UI after the specified existing command.
	control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, True)


# Executed when add-in is stopped.
def stop():
	# Get the various UI elements for this command
	workspace = ui.workspaces.itemById(WORKSPACE_ID)
	panel = workspace.toolbarPanels.itemById(PANEL_ID)
	command_control = panel.controls.itemById(CMD_ID)
	command_definition = ui.commandDefinitions.itemById(CMD_ID)

	# Delete the button command control
	if command_control:
		command_control.deleteMe()

	# Delete the command definition
	if command_definition:
		command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Created Event')

	# https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
	inputs = args.command.commandInputs

	# TODO Define the dialog for your command by adding different inputs to the command.
	if design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
		ui.messageBox('This tool is optimized for direct design mode (Disabled History). Please consider switching mode.', 'Design Mode', adsk.core.MessageBoxButtonTypes.OKButtonType)

	# TODO add tooltips

	# Create image input
	inputs.addBoolValueInput('imageSelector', 'Image', False, RESOURCES_FOLDER+"/imageSelector", False)
	stringValueInput = inputs.addStringValueInput('selectedFileName', 'Selected Image', '')
	stringValueInput.isReadOnly = True

	# Create face selection
	selectionInput = inputs.addSelectionInput('faceSelector', 'Select Face', '')
	selectionInput.addSelectionFilter(adsk.core.SelectionCommandInput.PlanarFaces)
	selectionInput.setSelectionLimits(0)

	# Create image base selection
	selectionInput = inputs.addSelectionInput('baseSelector', 'Select Base Edge', '')
	selectionInput.addSelectionFilter(adsk.core.SelectionCommandInput.LinearEdges)
	selectionInput.setSelectionLimits(0)
	selectionInput.isVisible = False
	selectionInput.isEnabled = False
	
	# Create image height mode
	dropDownInput = inputs.addDropDownCommandInput('dropDownSelector', 'Height Mode', adsk.core.DropDownStyles.TextListDropDownStyle)
	dropDownInput.isVisible = False
	dropDownInputList = dropDownInput.listItems
	dropDownInputList.add('Auto', True)
	dropDownInputList.add('Distance', False)
	dropDownInputList.add('Edge', False)
	
	# Create image height edge
	selectionInput = inputs.addSelectionInput('heightEdgeSelector', 'Select Height Edge', '')
	selectionInput.addSelectionFilter(adsk.core.SelectionCommandInput.LinearEdges)
	selectionInput.setSelectionLimits(0)
	selectionInput.isVisible = False
	selectionInput.isEnabled = False

	# Create image height distance
	initialValue = adsk.core.ValueInput.createByReal(0.1)
	heightInput = inputs.addDistanceValueCommandInput('heightSelector', 'Height', initialValue)
	heightInput.isVisible = False
	heightInput.minimumValue = 0
	heightInput.isMinimumValueInclusive = False

	# min thickness input
	initialValue = adsk.core.ValueInput.createByReal(0.1)
	minThicknessInput = inputs.addDistanceValueCommandInput('minThicknessSelector', 'Minimum Depth', initialValue)
	minThicknessInput.minimumValue = 0
	minThicknessInput.isMinimumValueInclusive = False
	minThicknessInput.isVisible = False

	# colorShiftCorrection
	initialValue = adsk.core.ValueInput.createByReal(2)
	colorShiftCorrection = inputs.addIntegerSliderCommandInput('colorShiftCorrectionSelector', 'Black/White distribution', -100, 100, False)
	colorShiftCorrection.valueOne = 0

	# Mode selection
	modeInput = inputs.addBoolValueInput('modeSelector', 'Flush Surface', True, '', True)
	modeInput.isEnabled = False

	# FlushBoundaryThickness
	initialValue = adsk.core.ValueInput.createByReal(2)
	flushBT = inputs.addValueInput('flushBTSelector', 'Outline Factor', '', initialValue)
	flushBT.isVisible = False

	# FixBroken selection
	fixBrokenInput = inputs.addBoolValueInput('fixBrokenSelector', 'Fix Missing Body', True, '', True)
	
	# TODO Connect to the events that are needed by this command.
	futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
	futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
	futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
	futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
	futil.add_handler(args.command.preSelect, command_select, local_handlers=local_handlers)
	futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
	# General logging for debug.
	if design.designType == adsk.fusion.DesignTypes.DirectDesignType:
		command_executeDirect(args)
	else:
		command_executeParametric(args)


def command_executeParametric(args: adsk.core.CommandEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Execute Parametric Event')
	# Get a reference to your command's inputs.
	inputs = args.command.commandInputs

	# TODO ******************************** Your code here ********************************

	fileNameInput = adsk.core.StringValueCommandInput.cast(inputs.itemById('selectedFileName'))
	fileName = fileNameInput.value
	
	faceSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))
	baseSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('baseSelector'))
	edgeSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('heightEdgeSelector'))
	heightInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('heightSelector'))
	modeInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('modeSelector'))
	fixBrokenInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('fixBrokenSelector'))
	minThicknessInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('minThicknessSelector'))
	flushBTInput = adsk.core.ValueCommandInput.cast(inputs.itemById('flushBTSelector'))
	colorShiftCorrectionInput = adsk.core.IntegerSliderCommandInput.cast(inputs.itemById('colorShiftCorrectionSelector'))

	face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
	base = adsk.fusion.BRepEdge.cast(baseSelectorInput.selection(0).entity)

	progressDialog = ui.createProgressDialog()
	progressDialog.cancelButtonText = 'Cancel'
	progressDialog.isBackgroundTranslucent = False
	progressDialog.isCancelButtonShown = True

	if face is None or base is None:
		return

	global loadedImage
	if loadedImage is None or not len(fileName) > 0:
		return
	
	try:
		
		image = loadedImage
		imageWidth, imageHeight = image.size
		
		# Load image
		loadedImage = loadedImage.transpose(Image.FLIP_TOP_BOTTOM)
		imageAsLine = list(loadedImage.getdata())
		futil.log('Image Raw: '+str(imageAsLine))
		
		if imageWidth*imageHeight > 2500 and ui.messageBox(f'This process can take several minutes depending on the size of the image.\nContinue?\n\nPixels to be processed: {imageWidth*imageHeight}','Expensive Operations Warning', adsk.core.MessageBoxButtonTypes.OKCancelButtonType) != adsk.core.DialogResults.DialogOK:
			return

		progressDialog.show('Generating Mono3D', 'Loading...', 0, 100, 0)
		
		widthInputValue = base.length
		cmPerPixel = (widthInputValue/imageWidth, 0)

		heightInputValue = cmPerPixel[0]*imageHeight
		if edgeSelectorInput.isVisible:
			edge = adsk.fusion.BRepEdge.cast(edgeSelectorInput.selection(0).entity)
			heightInputValue = edge.length
		elif heightInput.isVisible:
			heightInputValue = heightInput.value

		cmPerPixel = (cmPerPixel[0], heightInputValue/imageHeight)
		
		# Create new sketch, obtain creation objects
		sketch = design.rootComponent.sketches.add(face)
		sketchLines = sketch.sketchCurves.sketchLines
		extrudes = design.rootComponent.features.extrudeFeatures
		# Outline Image region width
		baseSketchLine: adsk.fusion.SketchLine = sketch.project(base)[0]

		# Calculate pixelVectors
		coEdge = getCoEdge(base, face)
		if coEdge is None:
			raise Exception('No CoEdge found')

		origin = baseSketchLine.startSketchPoint
		widthEndPoint = baseSketchLine.endSketchPoint

		if coEdge.isOpposedToEdge:
			origin, widthEndPoint = widthEndPoint, origin
		
		sketchFWidthVector = origin.geometry.vectorTo(widthEndPoint.geometry)
		sketchWidthVector = sketchFWidthVector.copy()
		sketchWidthVector.scaleBy(1/imageWidth)
		sketchHeightVector = adsk.core.Vector3D.create(-sketchWidthVector.y, sketchWidthVector.x, 0)
		sketchHeightVector.normalize()
		sketchHeightVector.scaleBy(cmPerPixel[1])
		sketchFHeightVector = sketchHeightVector.copy()
		sketchFHeightVector.scaleBy(imageHeight)


		# Outline Image region height
		tv = origin.geometry.asVector()
		mv = sketchHeightVector.copy()
		mv.scaleBy(imageHeight)
		tv.add(mv)

		heightSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())
		
		pixelFHeightVector = heightSketchLine.startSketchPoint.worldGeometry.vectorTo(heightSketchLine.endSketchPoint.worldGeometry)
		pixelFWidthVector = baseSketchLine.startSketchPoint.worldGeometry.vectorTo(baseSketchLine.endSketchPoint.worldGeometry)
		
		pixelHeightVector = pixelFHeightVector.copy()
		pixelHeightVector.scaleBy(1/imageHeight)
		pixelWidthVector = pixelFWidthVector.copy()
		pixelWidthVector.scaleBy(1/imageWidth)

		pixelOnePV = origin.worldGeometry.asVector()
		pixelOnePV.add(pixelHeightVector)
		pixelOnePV.add(pixelWidthVector)
		depthPoint, depth = getDepthPoint(face, pixelOnePV.asPoint())
		depth = minThicknessInput.value+0.1 if depthPoint is None else depth
		futil.log(f'Depth: {depth}')

		if minThicknessInput.value >= depth:
			raise Warning('Minimum Depth exceeds object depth.')

		faceNormal = face.evaluator.getNormalAtPoint(origin.worldGeometry)[1]
		faceNormal.normalize()

		# Outline Image depth
		nv = faceNormal.copy()
		nv.scaleBy(-depth)
		tv = origin.geometry.asVector()
		tv.add(nv)
		depthSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())
		sketch.isVisible = False

	
		# fixBroken
		if fixBrokenInput.value and not progressDialog.wasCancelled:
			
			# Create boundaries
			tv = origin.geometry.asVector()
			mv = sketchWidthVector.copy()
			mv.scaleBy(imageWidth)
			tv.add(mv)
			mv = sketchHeightVector.copy()
			mv.scaleBy(imageHeight)
			tv.add(mv)

			tlines = sketchLines.addThreePointRectangle(origin, widthEndPoint, tv.asPoint())
			outlineProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
			extrudeInput = extrudes.createInput(outlineProfiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
			extrudeInput.participantBodies = []
			extrudeInput.isSolid = True
			extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depth)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
			extrudes.add(extrudeInput)


		# Create Pattern
		startXPattern = (imageWidth > imageHeight)
		progressDialog.message = 'Sketching: %p% - %v/%m'
		for i in range(2):
			if startXPattern:
				progressDialog.maximumValue = imageWidth
				iv1 = origin.geometry.asVector()
				for l in range(imageWidth):
					if progressDialog.wasCancelled:
						break
					iv1.add(sketchWidthVector)
					iv2 = iv1.copy()
					iv2.add(sketchFHeightVector)
					sketchLines.addByTwoPoints(iv1.asPoint(), iv2.asPoint())
					progressDialog.progressValue = l+1
			
			else:
				progressDialog.maximumValue = imageHeight
				iv1 = origin.geometry.asVector()
				for l in range(imageHeight):
					if progressDialog.wasCancelled:
						break
					iv1.add(sketchHeightVector)
					iv2 = iv1.copy()
					iv2.add(sketchFWidthVector)
					sketchLine = sketchLines.addByTwoPoints(iv1.asPoint(), iv2.asPoint())
					progressDialog.progressValue = l+1
					
			startXPattern = not startXPattern

		# Map Profiles
		measureMgr = app.measureManager	
		
		colorProfileMapping = {}

		progressDialog.message = 'Mapping Pixels: %p% - %v/%m'
		progressDialog.maximumValue = sketch.profiles.count
		for i, p in enumerate(sketch.profiles):
			if progressDialog.wasCancelled:
				break
			pMidPoint = getPoint3DMidPoint(p.boundingBox.minPoint, p.boundingBox.maxPoint)
			pHI = int(measureMgr.measureMinimumDistance(baseSketchLine.geometry, pMidPoint).value / cmPerPixel[1])
			pWI = int(measureMgr.measureMinimumDistance(heightSketchLine.geometry, pMidPoint).value / cmPerPixel[0])
			pixelIndex = pHI*imageWidth + pWI
			futil.log(f'{i}/{sketch.profiles.count}: PixelIndex: {pWI}|{pHI} - {pixelIndex} -> {-pixelIndex/(imageHeight*imageWidth)*depth}\n{measureMgr.measureMinimumDistance(heightSketchLine.geometry, pMidPoint).value}')
			if pixelIndex > imageHeight*imageWidth:
				futil.log('HERE')#raise Exception(f'HERE {imageWidth}:{imageHeight}')
			else:
				colorProfileMapping.setdefault(imageAsLine[pixelIndex], []).append(p)
			progressDialog.progressValue = i+1

		# Extruding
		progressDialog.message = 'Extruding: %p% - %v/%m shades'
		progressDialog.maximumValue = 256

		futil.log(f'Depth: {depth}')

		# Iterate through color spectrum
		for e in range(256):
			if progressDialog.wasCancelled:
				break
			if e not in colorProfileMapping:
				continue

			extrudeProfiles = adsk.core.ObjectCollection.createWithArray(colorProfileMapping[e])

			shiftCorrection = max(min(255, e + colorShiftCorrectionInput.valueOne*0.01*255), 0)
			pixelDistance = (depth-minThicknessInput.value)/255*shiftCorrection
			futil.log(f'PixelGroup: {e} Distance: {pixelDistance}')
			futil.log(f'\tPixels: {len(colorProfileMapping[e])}')

			if pixelDistance == 0:
				continue

			extrudeInput = extrudes.createInput(extrudeProfiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
			extrudeInput.participantBodies = [face.body]
			extrudeInput.isSolid = True
			if not modeInput.value: # NOT FLUSH
				extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(pixelDistance)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
				exf = extrudes.add(extrudeInput)
				if exf.healthState == adsk.fusion.FeatureHealthStates.WarningFeatureHealthState:
					exf.deleteMe()

			else: # FLUSH
				extrudeInput.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(-(depth-minThicknessInput.value/2)))
				extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(pixelDistance)), adsk.fusion.ExtentDirections.PositiveExtentDirection)
				exf = extrudes.add(extrudeInput)
				if exf.healthState == adsk.fusion.FeatureHealthStates.WarningFeatureHealthState:
					exf.deleteMe()

			progressDialog.progressValue = e+1
	
		if not progressDialog.wasCancelled and modeInput.value and flushBTInput.value > 0: # FLUSH
			
			outlineProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
			extrudeInput = extrudes.createInput(outlineProfiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
			extrudeInput.isSolid = True
			extrudeInput.setThinExtrude(adsk.fusion.ThinExtrudeWallLocation.Side1, adsk.core.ValueInput.createByReal(cmPerPixel[0]/flushBTInput.value))
			extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depth)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
			extrudes.add(extrudeInput)

		if progressDialog.wasCancelled:
			args.executeFailed = True
			args.executeFailedMessage = 'Cancelled.'
		progressDialog.hide()
	except Exception as ex:
		futil.log(f'Exception caught: {traceback.format_exc()}')
		args.executeFailed = True
		args.executeFailedMessage = 'Error processing design.\n\n\n\n'+traceback.format_exc()

def command_executeDirect(args: adsk.core.CommandEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Execute Direct Event')
	# Get a reference to your command's inputs.
	inputs = args.command.commandInputs

	# TODO ******************************** Your code here ********************************

	fileNameInput = adsk.core.StringValueCommandInput.cast(inputs.itemById('selectedFileName'))
	fileName = fileNameInput.value
	
	faceSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))
	baseSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('baseSelector'))
	edgeSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('heightEdgeSelector'))
	heightInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('heightSelector'))
	modeInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('modeSelector'))
	fixBrokenInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('fixBrokenSelector'))
	minThicknessInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('minThicknessSelector'))
	flushBTInput = adsk.core.ValueCommandInput.cast(inputs.itemById('flushBTSelector'))
	colorShiftCorrectionInput = adsk.core.IntegerSliderCommandInput.cast(inputs.itemById('colorShiftCorrectionSelector'))

	face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
	base = adsk.fusion.BRepEdge.cast(baseSelectorInput.selection(0).entity)

	progressDialog = ui.createProgressDialog()
	progressDialog.cancelButtonText = 'Cancel'
	progressDialog.isBackgroundTranslucent = False
	progressDialog.isCancelButtonShown = True

	if face is None or base is None:
		return

	global loadedImage
	if loadedImage is None or not len(fileName) > 0:
		return
	
	try:
		image = loadedImage
		imageWidth, imageHeight = image.size
		
		# Load image
		loadedImage = loadedImage.transpose(Image.FLIP_TOP_BOTTOM)
		imageAsLine = list(loadedImage.getdata())
		futil.log('Image Raw: '+str(imageAsLine))
		futil.log(f'Image Size: {imageWidth*imageHeight}px')
		if imageWidth*imageHeight > 50000 and ui.messageBox(f'This process can take several minutes depending on the size of the image.\nContinue?\n\nPixels to be processed: {imageWidth*imageHeight}','Expensive Operations Warning', adsk.core.MessageBoxButtonTypes.OKCancelButtonType) != adsk.core.DialogResults.DialogOK:
			return
		
		progressDialog.show('Generating Mono3D', 'Loading...', 0, 100, 0)
		
		widthInputValue = base.length
		cmPerPixel = (widthInputValue/imageWidth, 0)

		heightInputValue = cmPerPixel[0]*imageHeight
		if edgeSelectorInput.isVisible:
			edge = adsk.fusion.BRepEdge.cast(edgeSelectorInput.selection(0).entity)
			heightInputValue = edge.length
		elif heightInput.isVisible:
			heightInputValue = heightInput.value

		cmPerPixel = (cmPerPixel[0], heightInputValue/imageHeight)
		
		# Create new sketch, obtain creation objects
		sketch = design.rootComponent.sketches.add(face)
		sketchLines = sketch.sketchCurves.sketchLines
		extrudes = design.rootComponent.features.extrudeFeatures
		# Outline Image region width
		baseSketchLine: adsk.fusion.SketchLine = sketch.project(base)[0]
		
		# Calculate pixelVectors
		coEdge = getCoEdge(base, face)
		if coEdge is None:
			raise Exception('No CoEdge found')

		origin = baseSketchLine.startSketchPoint
		widthEndPoint = baseSketchLine.endSketchPoint

		if coEdge.isOpposedToEdge:
			origin, widthEndPoint = widthEndPoint, origin
		
		sketchWidthVector = origin.geometry.vectorTo(widthEndPoint.geometry)
		sketchWidthVector.scaleBy(1/imageWidth)
		sketchHeightVector = adsk.core.Vector3D.create(-sketchWidthVector.y, sketchWidthVector.x, 0)
		sketchHeightVector.normalize()
		sketchHeightVector.scaleBy(cmPerPixel[1])


		# Outline Image region height
		tv = origin.geometry.asVector()
		mv = sketchHeightVector.copy()
		mv.scaleBy(imageHeight)
		tv.add(mv)

		heightSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())
		
		pixelFHeightVector = heightSketchLine.startSketchPoint.worldGeometry.vectorTo(heightSketchLine.endSketchPoint.worldGeometry)
		pixelFWidthVector = baseSketchLine.startSketchPoint.worldGeometry.vectorTo(baseSketchLine.endSketchPoint.worldGeometry)
		
		pixelHeightVector = pixelFHeightVector.copy()
		pixelHeightVector.scaleBy(1/imageHeight)
		pixelWidthVector = pixelFWidthVector.copy()
		pixelWidthVector.scaleBy(1/imageWidth)

		pixelOnePV = origin.worldGeometry.asVector()
		pixelOnePV.add(pixelHeightVector)
		pixelOnePV.add(pixelWidthVector)
		depthPoint, depth = getDepthPoint(face, pixelOnePV.asPoint())
		depth = minThicknessInput.value+0.1 if depthPoint is None else depth
		futil.log(f'Depth: {depth}')

		if minThicknessInput.value >= depth:
			raise Warning('Minimum Depth exceeds object depth.')

		faceNormal = face.evaluator.getNormalAtPoint(origin.worldGeometry)[1]
		faceNormal.normalize()

		# Outline Image depth
		nv = face.evaluator.getNormalAtPoint(origin.worldGeometry)[1]
		nv.normalize()
		nv.scaleBy(-depth)
		tv = origin.geometry.asVector()
		tv.add(nv)
		depthSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())
		sketch.isVisible = False

		# fixBroken
		if fixBrokenInput.value and not progressDialog.wasCancelled:
			
			# Create boundaries
			tv = origin.geometry.asVector()
			mv = sketchWidthVector.copy()
			mv.scaleBy(imageWidth)
			tv.add(mv)
			mv = sketchHeightVector.copy()
			mv.scaleBy(imageHeight)
			tv.add(mv)

			tlines = sketchLines.addThreePointRectangle(origin, widthEndPoint, tv.asPoint())
			outlineProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
			extrudeInput = extrudes.createInput(outlineProfiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
			extrudeInput.participantBodies = [face.body]
			extrudeInput.isSolid = True
			extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depth)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
			try:
				extrudes.add(extrudeInput)
			except RuntimeError:
				pass
		# Index Pixels
		pixelOriginIndex = {}

		progressDialog.message = 'Indexing Pixels: %p% - %v/%m'
		progressDialog.maximumValue = imageWidth*imageHeight
		for pixelIndex in range(imageWidth*imageHeight):
			if progressDialog.wasCancelled:
				break
			pHI = pixelIndex // imageWidth
			pWI = pixelIndex % imageWidth
			tv = origin.worldGeometry.asVector()
			mvH = pixelHeightVector.copy()
			mvH.scaleBy(pHI+0.5)
			tv.add(mvH)
			mvW = pixelWidthVector.copy()
			mvW.scaleBy(pWI+0.5)
			tv.add(mvW)

			pixelOriginIndex.setdefault(imageAsLine[pixelIndex], []).append(tv.asPoint())
			progressDialog.progressValue = pixelIndex+1

		
		# Modelling
		progressDialog.message = 'Modelling: %p% - %v/%m shades'
		progressDialog.maximumValue = 256
		
		tempBrepMgr = adsk.fusion.TemporaryBRepManager.get()

		faceTempBody = tempBrepMgr.copy(face.body)

		futil.log(f'Depth: {depth}')

		# Iterate through color spectrum
		for e in range(256):
			if progressDialog.wasCancelled:
				break
			if e not in pixelOriginIndex:
				continue

			shiftCorrection = max(min(255, e + colorShiftCorrectionInput.valueOne*0.01*255), 0)
			pixelDistance = (depth-minThicknessInput.value)/255*shiftCorrection
			futil.log(f'PixelGroup: {e} Distance: {pixelDistance}')
			futil.log(f'\tPixels: {len(pixelOriginIndex[e])}')

			if pixelDistance == 0:
				continue

			bodies = adsk.core.ObjectCollection.create()
			for op in pixelOriginIndex[e]:
				sop = op.asVector()
				fns = faceNormal.copy()
				fns.scaleBy(-pixelDistance/2)
				sop.add(fns)
				if modeInput.value: # FLUSH
					fns = faceNormal.copy()
					fns.scaleBy(-(depth-pixelDistance-minThicknessInput.value/2))
					sop.add(fns)
				op = sop.asPoint()

				orientedBox = adsk.core.OrientedBoundingBox3D.create(op, pixelWidthVector, pixelHeightVector, cmPerPixel[0], cmPerPixel[1], pixelDistance)
				tempBody = tempBrepMgr.createBox(orientedBox)
				bodies.add(tempBody)
				tempBrepMgr.booleanOperation(faceTempBody, tempBody, adsk.fusion.BooleanTypes.DifferenceBooleanType)

			progressDialog.progressValue = e+1
		newbody = design.rootComponent.bRepBodies.add(faceTempBody)
		newbody.name = 'Image2Mono3D'
		face.body.isVisible = False

		if not progressDialog.wasCancelled and modeInput.value and flushBTInput.value > 0: # FLUSH	
			outlineProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
			extrudeInput = extrudes.createInput(outlineProfiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
			extrudeInput.isSolid = True
			extrudeInput.participantBodies = [newbody]
			extrudeInput.setThinExtrude(adsk.fusion.ThinExtrudeWallLocation.Side1, adsk.core.ValueInput.createByReal(cmPerPixel[0]/flushBTInput.value))
			extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depth)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
			try:
				extrudes.add(extrudeInput)
			except:
				pass
		if progressDialog.wasCancelled:
			args.executeFailed = True
			args.executeFailedMessage = 'Cancelled.'
		progressDialog.hide()
		
	except Exception as ex:
		futil.log(f'Exception caught: {traceback.format_exc()}')
		args.executeFailed = True
		args.executeFailedMessage = 'Error processing design.\n\n\n\n'+traceback.format_exc()




# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Preview Event')
	inputs = args.command.commandInputs
	
	fileNameInput = adsk.core.StringValueCommandInput.cast(inputs.itemById('selectedFileName'))
	fileName = fileNameInput.value
	
	faceSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))
	baseSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('baseSelector'))
	edgeSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('heightEdgeSelector'))
	heightInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('heightSelector'))
	modeInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('modeSelector'))
	fixBrokenInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('fixBrokenSelector'))
	minThicknessInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('minThicknessSelector'))

	face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
	base = adsk.fusion.BRepEdge.cast(baseSelectorInput.selection(0).entity)

	if face is None or base is None:
		return

	global loadedImage
	if loadedImage is None or not len(fileName) > 0:
		return
	
	try:
		image = loadedImage
		imageWidth, imageHeight = image.size
		widthInputValue = base.length
		cmPerPixel = (widthInputValue/imageWidth, 0)

		heightInputValue = cmPerPixel[0]*imageHeight
		if edgeSelectorInput.isVisible:
			edge = adsk.fusion.BRepEdge.cast(edgeSelectorInput.selection(0).entity)
			heightInputValue = edge.length
		elif heightInput.isVisible:
			heightInputValue = heightInput.value

		cmPerPixel = (cmPerPixel[0], heightInputValue/imageHeight)
		
		# Create new sketch, obtain creation objects
		sketch = design.rootComponent.sketches.add(face)
		sketchLines = sketch.sketchCurves.sketchLines
		extrudes = design.rootComponent.features.extrudeFeatures

		# Outline Image region width
		baseSketchLine: adsk.fusion.SketchLine = sketch.project(base)[0]

		# Calculate pixelVectors
		coEdge = getCoEdge(base, face)
		if coEdge is None:
			raise Exception('No CoEdge found')

		origin = baseSketchLine.startSketchPoint
		widthEndPoint = baseSketchLine.endSketchPoint

		if coEdge.isOpposedToEdge:
			origin, widthEndPoint = widthEndPoint, origin
		
		sketchWidthVector = origin.geometry.vectorTo(widthEndPoint.geometry)
		sketchWidthVector.scaleBy(1/imageWidth)
		sketchHeightVector = adsk.core.Vector3D.create(-sketchWidthVector.y, sketchWidthVector.x, 0)
		sketchHeightVector.normalize()
		sketchHeightVector.scaleBy(cmPerPixel[1])


		# Outline Image region height
		tv = origin.geometry.asVector()
		mv = sketchHeightVector.copy()
		mv.scaleBy(imageHeight)
		tv.add(mv)

		heightSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())
		
		pixelFHeightVector = heightSketchLine.startSketchPoint.worldGeometry.vectorTo(heightSketchLine.endSketchPoint.worldGeometry)
		pixelFWidthVector = baseSketchLine.startSketchPoint.worldGeometry.vectorTo(baseSketchLine.endSketchPoint.worldGeometry)
		
		pixelHeightVector = pixelFHeightVector.copy()
		pixelHeightVector.scaleBy(1/imageHeight)
		pixelWidthVector = pixelFWidthVector.copy()
		pixelWidthVector.scaleBy(1/imageWidth)

		pixelOnePV = origin.worldGeometry.asVector()
		pixelOnePV.add(pixelHeightVector)
		pixelOnePV.add(pixelWidthVector)
		depthPoint, depth = getDepthPoint(face, pixelOnePV.asPoint())
		depth = minThicknessInput.value+0.1 if depthPoint is None else depth
		futil.log(f'Depth: {depth}')

		# Outline Image depth
		nv = face.evaluator.getNormalAtPoint(origin.worldGeometry)[1]
		nv.normalize()
		nv.scaleBy(-depth)
		tv = origin.geometry.asVector()
		tv.add(nv)
		depthSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())
	
		# extrude after canvas
		if fixBrokenInput.value:
			if design.designType == adsk.fusion.DesignTypes.DirectDesignType:
				face.body.isVisible = False
			# Create boundaries
			tv = origin.geometry.asVector()
			mv = sketchWidthVector.copy()
			mv.scaleBy(imageWidth)
			tv.add(mv)
			mv = sketchHeightVector.copy()
			mv.scaleBy(imageHeight)
			tv.add(mv)

			tlines = sketchLines.addThreePointRectangle(origin, widthEndPoint, tv.asPoint())
			# prepare extrusion, wait for canvas
			inputProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
			extrude = extrudes.addSimple(inputProfiles, adsk.core.ValueInput.createByReal(-depth), adsk.fusion.FeatureOperations.JoinFeatureOperation)

			sketch.isVisible = True
	except Exception as ex:
		futil.log(f'Exception caught: {traceback.format_exc()}')
		ui.messageBox('Error processing preview: '+str(ex))

# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
	changed_input = args.input
	inputs = args.inputs
	
	updateDropDown = False

	if changed_input.id == 'imageSelector':
		fileDialog = ui.createFileDialog()
		fileDialog.filter = 'Image Files (*.BMP;*.JPG;*.PNG);;All files (*.*)'
		fileDialog.filterIndex = 0
		fileDialog.isMultiSelectEnabled = False
		fileDialog.title = 'Select Image File'
		result = fileDialog.showOpen()
		if result == adsk.core.DialogResults.DialogOK:
			fileNameInput = adsk.core.StringValueCommandInput.cast(inputs.itemById('selectedFileName'))
			fileName = fileDialog.filename
			global loadedImage
			try:
				image = Image.open(fileName).convert('L')
				image.verify()
				loadedImage = image
			except Exception as ex:
				futil.log(f'Exception caught: {traceback.format_exc()}')
				ui.messageBox('Invalid Image File: '+str(ex))
				fileName = ''
				loadedImage = None

			fileNameInput.value = fileName
			fileNameInput.tooltip = fileName
			
	if changed_input.id == 'faceSelector':
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(changed_input)
		baseSelectionInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('baseSelector'))
		modeInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('modeSelector'))
		flushBTInput = adsk.core.ValueCommandInput.cast(inputs.itemById('flushBTSelector'))
		dropDownInput = adsk.core.DropDownCommandInput.cast(inputs.itemById('dropDownSelector'))
		minThicknessInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('minThicknessSelector'))
		try:
			face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
			modeInput.isEnabled = True
			flushBTInput.isVisible = modeInput.value
			baseSelectionInput.isVisible = True
			baseSelectionInput.isEnabled = True
			
		except Exception as ex:
			futil.log(f'Exception caught: {traceback.format_exc()}')
			modeInput.isEnabled = False
			flushBTInput.isVisible = False
			baseSelectionInput.isVisible = False
			baseSelectionInput.isEnabled = False
			updateDropDown = True
			dropDownInput.isVisible = False
			minThicknessInput.isVisible = False

	if changed_input.id == 'modeSelector':
		modeInput = adsk.core.BoolValueCommandInput.cast(changed_input)
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))
		flushBTInput = adsk.core.ValueCommandInput.cast(inputs.itemById('flushBTSelector'))
		flushBTInput.isVisible = modeInput.value

	if changed_input.id == 'baseSelector':
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))
		edgeSelectorInput = adsk.core.SelectionCommandInput.cast(changed_input)
		dropDownInput = adsk.core.DropDownCommandInput.cast(inputs.itemById('dropDownSelector'))
		minThicknessInput = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('minThicknessSelector'))
		edgeSelector = inputs.itemById('heightEdgeSelector')
		distanceSelector = inputs.itemById('heightSelector')
		distanceSelector = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('heightSelector'))
		updateDropDown = True
		
		try:
			face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
			edge = adsk.fusion.BRepEdge.cast(edgeSelectorInput.selection(0).entity)
			
			dropDownInput.isVisible = True
			minThicknessInput.isVisible = True

			coEdge = getCoEdge(edge, face)
			if coEdge is None:
				raise Exception('No CoEdge found')

			edgeEndPoints = edge.evaluator.getEndPoints()[1:]
			if coEdge.isOpposedToEdge:
				edgeEndPoints = edgeEndPoints[::-1]
			faceNormal = face.evaluator.getNormalAtPoint(edgeEndPoints[0])[1]
			faceNormal.normalize()
			edgeVect = edgeEndPoints[0].vectorTo(edgeEndPoints[1])
			paramVector = faceNormal.crossProduct(edgeVect)
			paramVector.normalize()

			distanceSelector.setManipulator(edgeEndPoints[0], paramVector)
			fn = faceNormal.copy()
			fn.scaleBy(-1)
			minThicknessInput.setManipulator(edgeEndPoints[0], fn)

		except Exception as ex:
			futil.log(f'Exception caught: {traceback.format_exc()}')
			dropDownInput.isVisible = False
			minThicknessInput.isVisible = False

	if updateDropDown or changed_input.id == 'dropDownSelector':
		dropDownInput = adsk.core.DropDownCommandInput.cast(changed_input)
		if updateDropDown:
			dropDownInput = adsk.core.DropDownCommandInput.cast(inputs.itemById('dropDownSelector'))
		edgeSelector = inputs.itemById('heightEdgeSelector')
		distanceSelector = inputs.itemById('heightSelector')

		if not dropDownInput.isVisible or dropDownInput.selectedItem.name == 'Auto':
			edgeSelector.isVisible = False
			edgeSelector.isEnabled = False
			distanceSelector.isVisible = False
		elif dropDownInput.selectedItem.name == 'Distance':
			edgeSelector.isVisible = False
			edgeSelector.isEnabled = False
			distanceSelector.isVisible = True
		elif dropDownInput.selectedItem.name == 'Edge':
			edgeSelector.isVisible = True
			edgeSelector.isEnabled = True
			distanceSelector.isVisible = False


	# General logging for debug.
	futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Validate Input Event')
	inputs = args.inputs

	fileNameInput = adsk.core.StringValueCommandInput.cast(inputs.itemById('selectedFileName'))
	if not len(fileNameInput.value) > 0:
		args.areInputsValid = False
	
	faceSelector = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))
	if faceSelector.isVisible and not faceSelector.selectionCount == 1:
		args.areInputsValid = False
	
	baseSelector = adsk.core.SelectionCommandInput.cast(inputs.itemById('baseSelector'))
	if baseSelector.isVisible and not baseSelector.selectionCount == 1:
		args.areInputsValid = False
	
	edgeSelector = adsk.core.SelectionCommandInput.cast(inputs.itemById('heightEdgeSelector'))
	if edgeSelector.isVisible and not edgeSelector.selectionCount == 1:
		args.areInputsValid = False

	flushBTInput = adsk.core.ValueCommandInput.cast(inputs.itemById('flushBTSelector'))
	if flushBTInput.isVisible and flushBTInput.value < 0:
		args.areInputsValid = False

# This event handler is called when the selection changes.
def command_select(args: adsk.core.SelectionEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Selection Event')
	
	if args.activeInput.selectionCount > 0:
		args.isSelectable = False
		return

	if args.activeInput.id == 'baseSelector':
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(args.activeInput.commandInputs.itemById('faceSelector'))
		try:
			face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
			base = adsk.fusion.BRepEdge.cast(args.selection.entity)
			if face not in base.faces:
				args.isSelectable = False
		except Exception as ex:
			futil.log(f'Exception caught: {traceback.format_exc()}')
			args.isSelectable = False
	
	if args.activeInput.id == 'heightEdgeSelector':
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(args.activeInput.commandInputs.itemById('faceSelector'))
		baseSelectorInput = adsk.core.SelectionCommandInput.cast(args.activeInput.commandInputs.itemById('baseSelector'))
		try:
			face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
			base = adsk.fusion.BRepEdge.cast(baseSelectorInput.selection(0).entity)
			edge = adsk.fusion.BRepEdge.cast(args.selection.entity)
			if face not in edge.faces:
				args.isSelectable = False
			
			basePoints = base.evaluator.getEndPoints()[1:]
			edgePoints = edge.evaluator.getEndPoints()[1:]
			v1 = basePoints[0].vectorTo(basePoints[1])
			v2 = edgePoints[0].vectorTo(edgePoints[1])
			if not v1.isPerpendicularTo(v2):
				args.isSelectable = False
		except Exception as ex:
			futil.log(f'Exception caught: {traceback.format_exc()}')
			args.isSelectable = False


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Destroy Event')

	global local_handlers
	local_handlers = []


# Return BRepCoEdge of edge and face
def getCoEdge(edge: adsk.fusion.BRepEdge, face: adsk.fusion.BRepFace) -> adsk.fusion.BRepCoEdge:
	edgeCoEdge = None
	for coEdge in edge.coEdges:
		if coEdge.loop.face == face:
			edgeCoEdge = coEdge
			break
	return edgeCoEdge


# Point3D MidPoint
def getPoint3DMidPoint(point1: adsk.core.Point3D, point2: adsk.core.Point3D):
	return adsk.core.Point3D.create((point1.x+point2.x)/2, (point1.y+point2.y)/2, (point1.z+point2.z)/2)


def getDepthPoint(face, origin):
	depthRay = adsk.core.InfiniteLine3D.create(origin, face.evaluator.getNormalAtPoint(origin)[1])
	depthPoint = None
	depth = 0
	for f in face.body.faces:
		if f == face:
			continue
		intersectionPoints = depthRay.intersectWithSurface(f.geometry)
		for ip in intersectionPoints:
			pcont = f.body.pointContainment(ip)
			if pcont != adsk.fusion.PointContainment.PointOnPointContainment and pcont != adsk.fusion.PointContainment.PointInsidePointContainment:
				continue
			futil.log(f't: {ip.distanceTo(origin)}')
			if ip.distanceTo(origin) > depth:
				depthPoint = ip
				depth = ip.distanceTo(origin)

	return (depthPoint, depth)
			