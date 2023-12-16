import adsk.core, adsk.fusion
import os, traceback, tempfile
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
tempFileName = ''

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

	# Mode selection
	modeInput = inputs.addBoolValueInput('modeSelector', 'Flush Surface', True, '', True)
	modeInput.isEnabled = False

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
	futil.log(f'{CMD_NAME} Command Execute Event')
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

		patternDepth = 0.1
		
		if imageWidth*imageHeight > 2500 and ui.messageBox(f'This process can take several minutes depending on the size of the image.\nContinue?\n\nPixels to be processed: {imageWidth*imageHeight}','Expensive Operations Warning', adsk.core.MessageBoxButtonTypes.OKCancelButtonType) != adsk.core.DialogResults.DialogOK:
			return

		progressDialog.show('Generating Mono3D', 'Applying pattern. (Fusion360)', 0, 256, 0)
		
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
		rectangularPatterns = design.rootComponent.features.rectangularPatternFeatures
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
		
		pixelWidthVector = origin.geometry.vectorTo(widthEndPoint.geometry)
		pixelWidthVector.scaleBy(1/imageWidth)
		pixelHeightVector = adsk.core.Vector3D.create(-pixelWidthVector.y, pixelWidthVector.x, 0)
		pixelHeightVector.normalize()
		pixelHeightVector.scaleBy(cmPerPixel[1])

		pixelFHeightVector = pixelHeightVector.copy()
		pixelFHeightVector.scaleBy(imageHeight)
		pixelFWidthVector = pixelWidthVector.copy()
		pixelFWidthVector.scaleBy(imageWidth)

		# Outline Image region height
		tv = origin.geometry.asVector()
		tv.add(pixelFHeightVector)

		heightSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())
		
		# TODO calc body thickness (not with depth Edge)
		# TODO stretch interior option

		# find depth Edge
		depthEdge = None
		for bedges in face.body.edges:
			bedgeVect = bedges.evaluator.getEndPoints()[1].vectorTo(bedges.evaluator.getEndPoints()[2])
			if not bedgeVect.isParallelTo(face.evaluator.getNormalAtPoint(origin.worldGeometry)[1]):
				continue
			if bedges.startVertex == base.startVertex or bedges.startVertex == base.endVertex or bedges.endVertex == base.startVertex or bedges.endVertex == base.endVertex:
				depthEdge = bedges
				break
		if depthEdge is None:
			raise Exception('Cannot determine object depth.')

		depthEdgeLength = depthEdge.length

		if minThicknessInput.value >= depthEdgeLength:
			raise Exception('Minimum Depth exceeds object depth.')

		# Outline Image depth
		nv = face.evaluator.getNormalAtPoint(origin.worldGeometry)[1]
		nv.normalize()
		nv.scaleBy(-depthEdgeLength)
		tv = origin.geometry.asVector()
		tv.add(nv)
		depthSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(origin, tv.asPoint())

		# Create Pattern
		iv1 = origin.geometry.asVector()
		iv1.add(pixelHeightVector)
		iv1.add(pixelWidthVector)
		rectangle = sketchLines.addTwoPointRectangle(origin.geometry, iv1.asPoint())
		inputProfiles = adsk.core.ObjectCollection.create()
		notProf = sketch.profiles.item(0)
		for p in sketch.profiles:
			inputProfiles.add(p)
			if p.areaProperties().area > notProf.areaProperties().area:
				notProf = p
		
		inputProfiles.removeByItem(notProf)
		extrude = extrudes.addSimple(inputProfiles, adsk.core.ValueInput.createByReal(patternDepth), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)


		
		# fixBroken
		if fixBrokenInput.value:
			# Create boundaries
			tv = origin.geometry.asVector()
			tv.add(pixelFHeightVector)
			tv.add(pixelFWidthVector)
			sketchLines.addTwoPointRectangle(origin, tv.asPoint())

			outlineProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
			extrudeInput = extrudes.createInput(outlineProfiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
			extrudeInput.participantBodies = [face.body]
			extrudeInput.isSolid = True
			extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depthEdgeLength)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
			extrudes.add(extrudeInput)
			
		inputEntities = adsk.core.ObjectCollection.create()
		inputEntities.add(extrude.bodies.item(0))

		rectangularPatternsInput = rectangularPatterns.createInput(inputEntities, baseSketchLine, adsk.core.ValueInput.createByReal(imageWidth), adsk.core.ValueInput.createByReal(widthInputValue-cmPerPixel[0]), adsk.fusion.PatternDistanceType.ExtentPatternDistanceType)
		rectangularPatternsInput.setDirectionTwo(heightSketchLine, adsk.core.ValueInput.createByReal(imageHeight), adsk.core.ValueInput.createByReal(heightInputValue-cmPerPixel[1]))
		rectangularFeature = rectangularPatterns.add(rectangularPatternsInput)
	
		pixelBodies = [extrude.bodies.item(0)]+[b for b in rectangularFeature.bodies]
		
		# Extruding
		progressDialog.message = 'Extruding: %p% - %v/%m shades'
		
		faceNormal = face.evaluator.getNormalAtPoint(face.centroid)[1]
		faceNormal.normalize()

		loadedImage = loadedImage.transpose(Image.FLIP_TOP_BOTTOM)
		imageAsLine = list(loadedImage.getdata())

		colorBodyMapping = {}
		for e in range(0, imageHeight*imageWidth):
			colorBodyMapping.setdefault(imageAsLine[e], []).append(pixelBodies[e])

		futil.log('Image Raw: '+str(imageAsLine))
		futil.log(str(depthEdgeLength))

		# Iterate through color spectrum
		for e in range(256):
			if progressDialog.wasCancelled:
				break
			if e not in colorBodyMapping:
				continue

			# Gather all Top Faces
			extrudeFaces = adsk.core.ObjectCollection.create()
			for body in colorBodyMapping[e]:
				extrudeFace = None
				for f in body.faces:
					fn = f.evaluator.getNormalAtPoint(f.centroid)[1]
					fn.normalize()
					if fn.isEqualTo(faceNormal):
						extrudeFace = f
						break
				if extrudeFace is None:
					raise Exception('Cannot find top face of colorBody')
				extrudeFaces.add(extrudeFace)


			if not modeInput.value: # NOT FLUSH
				
				pixelDistance = (depthEdgeLength-minThicknessInput.value)/255*e
				futil.log(f'PixelGroup: {e} Distance: {pixelDistance}')
				futil.log(f'\tPixels: {len(colorBodyMapping[e])}')
				extrudeInput = extrudes.createInput(extrudeFaces, adsk.fusion.FeatureOperations.CutFeatureOperation)
				extrudeInput.participantBodies = [face.body] + colorBodyMapping[e]
				extrudeInput.isSolid = True
				extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(pixelDistance+patternDepth)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
				extrudes.add(extrudeInput)

			else: # FLUSH
				
				pixelDistance = (depthEdgeLength-minThicknessInput.value)/255*e
				futil.log(f'PixelGroup: {e} Distance: {pixelDistance}')
				futil.log(f'\tPixels: {len(colorBodyMapping[e])}')
				extrudeInput = extrudes.createInput(extrudeFaces, adsk.fusion.FeatureOperations.CutFeatureOperation)
				extrudeInput.participantBodies = [face.body]
				extrudeInput.isSolid = True
				extrudeInput.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(-(minThicknessInput.value/2+patternDepth)))
				extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(pixelDistance)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
				exf = extrudes.add(extrudeInput)
				if exf.healthState == adsk.fusion.FeatureHealthStates.WarningFeatureHealthState:
					exf.deleteMe()

				extrudeInput = extrudes.createInput(extrudeFaces, adsk.fusion.FeatureOperations.CutFeatureOperation)
				extrudeInput.participantBodies = colorBodyMapping[e]
				extrudeInput.isSolid = True
				extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(patternDepth)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
				extrudes.add(extrudeInput)

			progressDialog.progressValue = e+1
	
		if modeInput.value: # FLUSH
			
			outlineProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
			extrudeInput = extrudes.createInput(outlineProfiles, adsk.fusion.FeatureOperations.JoinFeatureOperation)
			extrudeInput.isSolid = True
			extrudeInput.setThinExtrude(adsk.fusion.ThinExtrudeWallLocation.Center, adsk.core.ValueInput.createByReal(cmPerPixel[0]/10))
			extrudeInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depthEdgeLength)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
			extrudes.add(extrudeInput)

		# Merge everything
		if not progressDialog.wasCancelled and not modeInput.value:
			progressDialog.message = 'Merging. (Fusion360)'
			
			combineFeatures = design.rootComponent.features.combineFeatures
		
			combineObjects = adsk.core.ObjectCollection.createWithArray([r for r in rectangularFeature.bodies])
			combineInput = combineFeatures.createInput(face.body, combineObjects)
			combineInput.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
			combineFeatureList = combineFeatures.add(combineInput)

		if progressDialog.wasCancelled:
			args.executeFailed = True
			args.executeFailedMessage = 'Cancelled.'
		progressDialog.hide()
	except:
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

		sketchOrigin = baseSketchLine.startSketchPoint
		sketchWidthEndPoint = baseSketchLine.endSketchPoint

		if coEdge.isOpposedToEdge:
			sketchOrigin, sketchWidthEndPoint = sketchWidthEndPoint, sketchOrigin
		
		pixelWidthVector = sketchOrigin.geometry.vectorTo(sketchWidthEndPoint.geometry)
		pixelWidthVector.scaleBy(1/imageWidth)
		pixelHeightVector = adsk.core.Vector3D.create(-pixelWidthVector.y, pixelWidthVector.x, 0)
		pixelHeightVector.normalize()
		pixelHeightVector.scaleBy(cmPerPixel[1])

		pixelFHeightVector = pixelHeightVector.copy()
		pixelFHeightVector.scaleBy(imageHeight)
		pixelFWidthVector = pixelWidthVector.copy()
		pixelFWidthVector.scaleBy(imageWidth)

		# Outline Image region height
		tv = sketchOrigin.geometry.asVector()
		tv.add(pixelFHeightVector)

		heightSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(sketchOrigin, tv.asPoint())
		
		# Create boundaries
		tv.add(pixelFWidthVector)
		sketchLines.addTwoPointRectangle(sketchOrigin, tv.asPoint())

		# find depth Edge
		depthEdge = None
		for bedges in face.body.edges:
			bedgeVect = bedges.evaluator.getEndPoints()[1].vectorTo(bedges.evaluator.getEndPoints()[2])
			if not bedgeVect.isParallelTo(face.evaluator.getNormalAtPoint(sketchOrigin.worldGeometry)[1]):
				continue
			if bedges.startVertex == base.startVertex or bedges.startVertex == base.endVertex or bedges.endVertex == base.startVertex or bedges.endVertex == base.endVertex:
				depthEdge = bedges
				break
		if depthEdge is None:
			raise Exception('Cannot determine object depth.')

		# Outline Image depth
		nv = face.evaluator.getNormalAtPoint(sketchOrigin.worldGeometry)[1]
		nv.normalize()
		nv.scaleBy(-depthEdge.length)
		tv = sketchOrigin.geometry.asVector()
		tv.add(nv)
		depthSketchLine: adsk.fusion.SketchLine = sketchLines.addByTwoPoints(sketchOrigin, tv.asPoint())
		
		# prepare extrusion, wait for canvas
		inputProfiles = adsk.core.ObjectCollection.createWithArray([x for x in sketch.profiles])
		
		# Save image as tmpFile to use as Canvas, tmp file is deleted after with scope
		global tempFileName
		if len(tempFileName) > 0:
			os.remove(tempFileName)
			tempFileName = ''

		# Canvas preview
		with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
			tempFileName = tf.name
			loadedImage.save(tf, 'PNG')
			tf.close()
			# Create canvas

			bounds = face.evaluator.parametricRange()
			uvCenter = adsk.core.Point2D.create(0, 0)
		
			v2D1 = adsk.core.Vector2D.create(pixelFWidthVector.asArray()[0], pixelFWidthVector.asArray()[1])
			v2D2 = adsk.core.Vector2D.create(pixelFHeightVector.asArray()[0], pixelFHeightVector.asArray()[1])
		
			canvasInput = design.rootComponent.canvases.createInput(tempFileName, face)
			bounds = face.evaluator.parametricRange()
			uvCenter = adsk.core.Point2D.create((bounds.minPoint.x + bounds.maxPoint.x)/2, (bounds.minPoint.y + bounds.maxPoint.y)/2)
			vectorToTarget = uvCenter.vectorTo(coEdge.evaluator.getEndPoints()[1])
			if face.isParamReversed:
				vectorToTarget.x *= -1
				
			matrix = adsk.core.Matrix2D.create()
			matrixOriginVect = uvCenter.asVector()
			matrixOriginVect.add(vectorToTarget)
			matrix = canvasInput.transform
			matrix.setWithCoordinateSystem(matrixOriginVect.asPoint(), v2D1, v2D2)
			canvasInput.transform = matrix
			canvasInput.opacity = 100
			canvas = design.rootComponent.canvases.add(canvasInput)

		# extrude after canvas
		if fixBrokenInput.value:
			extrude = extrudes.addSimple(inputProfiles, adsk.core.ValueInput.createByReal(-depthEdge.length), adsk.fusion.FeatureOperations.JoinFeatureOperation)


	except:
		futil.log(f'Exception caught: {traceback.format_exc()}')
		ui.messageBox('Error processing preview')

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
			except:
				futil.log(f'Exception caught: {traceback.format_exc()}')
				ui.messageBox('Invalid Image File')
				fileName = ''
				loadedImage = None

			fileNameInput.value = fileName
			fileNameInput.tooltip = fileName
			
	if changed_input.id == 'faceSelector':
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(changed_input)
		baseSelectionInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('baseSelector'))
		modeInput = adsk.core.BoolValueCommandInput.cast(inputs.itemById('modeSelector'))
		dropDownInput = adsk.core.DropDownCommandInput.cast(inputs.itemById('dropDownSelector'))
		try:
			face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
			modeInput.isEnabled = True
			baseSelectionInput.isVisible = True
			baseSelectionInput.isEnabled = True
			
		except:
			futil.log(f'Exception caught: {traceback.format_exc()}')
			modeInput.isEnabled = False
			baseSelectionInput.isVisible = False
			baseSelectionInput.isEnabled = False
			updateDropDown = True
			dropDownInput.isVisible = False

	if changed_input.id == 'modeSelector':
		modeInput = adsk.core.BoolValueCommandInput.cast(changed_input)
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))

	if changed_input.id == 'baseSelector':
		faceSelectorInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('faceSelector'))
		edgeSelectorInput = adsk.core.SelectionCommandInput.cast(changed_input)
		dropDownInput = adsk.core.DropDownCommandInput.cast(inputs.itemById('dropDownSelector'))
		edgeSelector = inputs.itemById('heightEdgeSelector')
		distanceSelector = inputs.itemById('heightSelector')
		distanceSelector = adsk.core.DistanceValueCommandInput.cast(inputs.itemById('heightSelector'))
		updateDropDown = True
		
		try:
			face = adsk.fusion.BRepFace.cast(faceSelectorInput.selection(0).entity)
			edge = adsk.fusion.BRepEdge.cast(edgeSelectorInput.selection(0).entity)
			
			dropDownInput.isVisible = True

			coEdge = getCoEdge(edge, face)
			if coEdge is None:
				raise Exception('No CoEdge found')

			# TODO draft edges issue

			edgeEndPoints = edge.evaluator.getEndPoints()[1:]
			if coEdge.isOpposedToEdge:
				edgeEndPoints = edgeEndPoints[::-1]
			faceNormal = face.evaluator.getNormalAtPoint(edgeEndPoints[0])[1]
			edgeVect = edgeEndPoints[0].vectorTo(edgeEndPoints[1])
			paramVector = faceNormal.crossProduct(edgeVect)
			paramVector.normalize()

			distanceSelector.setManipulator(edgeEndPoints[0], paramVector)
		except:
			futil.log(f'Exception caught: {traceback.format_exc()}')
			dropDownInput.isVisible = False

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
		except:
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
		except:
			futil.log(f'Exception caught: {traceback.format_exc()}')
			args.isSelectable = False


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Destroy Event')

	global local_handlers
	local_handlers = []
	global tempFileName
	if len(tempFileName) > 0:
		os.remove(tempFileName)
		tempFileName = ''


# Return BRepCoEdge of edge and face
def getCoEdge(edge: adsk.fusion.BRepEdge, face: adsk.fusion.BRepFace) -> adsk.fusion.BRepCoEdge:
	edgeCoEdge = None
	for coEdge in edge.coEdges:
		if coEdge.loop.face == face:
			edgeCoEdge = coEdge
			break
	return edgeCoEdge