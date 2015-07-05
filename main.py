from math import pi, sin, cos, radians, log
from random import randint, choice, random
from time import clock
from sys import exit
 
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from direct.gui.DirectGui import *

from pandac.PandaModules import WindowProperties
from pandac.PandaModules import TextureStage, Texture
from pandac.PandaModules import TexGenAttrib

from panda3d.core import Point3, BitMask32, Vec3
from panda3d.core import CollisionTraverser, CollisionNode, CollisionHandlerFloor
from panda3d.core import CollisionHandlerEvent, CollisionSphere, CollisionRay
from panda3d.core import GeoMipTerrain, loadPrcFileData
from panda3d.core import Fog
from panda3d.physics import *

#Display modes

MAIN_MENU = 0
PLAY = 1
IN_GAME_MENU = 2

#Play modes

TERRAIN = 0
SPACE = 1
DEAD = 2

LEVEL = 1

class GameObject(object):

    def __init__(self, objectNP):

        self.objectNP = objectNP

        self.objectNP.reparentTo(render)

    def getWrappedSphere(self):

        tightBounds = self.objectNP.getBounds()

        sphereCenter = tightBounds.getCenter()
        sphereRadius = tightBounds.getRadius()

        return CollisionSphere(sphereCenter, sphereRadius)

    def __del__(self):

        self.objectNP.removeNode()

class Avatar(GameObject):

    LAND_GAP_PERMISSION = 5

    def __init__(self, objectNP, level):

        GameObject.__init__(self, objectNP)

        self.speed = Vec3(0, 0, 0)

        self.yawRot = 0

        self.landed = False
        self.landGap = 0
        self.jumpThrusting = False
        self.jumpThrustInterval = 10 
        self.jumpThrustCounter = self.jumpThrustInterval

        self.states = {"alive" : True}

        self.calcLimits(level)

    def calcLimits(self, level):

        self.SPACE_SPEED = -8

        self.max_velocity_terrain = (5, 15, 0)
        self.max_velocity_space = (5, SPACE_SPEED , 5)

        self.acceleration_terrain = (1, 5, 0)
        self.acceleration_space = (-1, 0, -1)

    def move(self, dt):

        #Relative to own coordinate system

        self.objectNP.setPos(self.objectNP, self.speed[0]*dt, self.speed[1]*dt, self.speed[2]*dt)

        if self.jumpThrusting:

            self.landed = False

            if self.jumpThrustCounter < self.jumpThrustInterval:

                self.jumpThrustCounter += 1

            else:

                self.objectNP.node().getPhysical(0).removeLinearForce(self.jumpThrustForce)

                self.jumpThrusting = False

    def handleKeys(self, keys, play_mode):

        if play_mode == TERRAIN:

            if keys["w"]: self.speed[1] += Avatar.acceleration_terrain[1]
            if keys["s"]: self.speed[1] += -Avatar.acceleration_terrain[1]
            if keys["a"]: self.speed[0] += -Avatar.acceleration_terrain[0]
            if keys["d"]: self.speed[0] += Avatar.acceleration_terrain[0]

            speedBound = Avatar.max_velocity_terrain

        elif play_mode == SPACE:

            if keys["w"]: self.speed[2] += Avatar.acceleration_space[2]
            if keys["s"]: self.speed[2] += -Avatar.acceleration_space[2]
            if keys["a"]: self.speed[0] += -Avatar.acceleration_space[0]
            if keys["d"]: self.speed[0] += Avatar.acceleration_space[0]

            self.speed[1] = Avatar.SPACE_SPEED

            speedBound = Avatar.max_velocity_space

        for i, bound in enumerate(speedBound):

            if abs(self.speed[i]) > bound:

                closerBound = min((-bound, bound), key=lambda x: abs(self.speed[i]-x))

                self.speed[i] = closerBound

        if keys["space"]:

            if self.landed and self.jumpThrustCounter == self.jumpThrustInterval and \
                           not self.jumpThrusting:

                    self.landed = False
                    self.jumpThrusting = True
                    self.jumpThrustCounter = 0

                    self.jumpThrustForce = LinearVectorForce(0, 0, 50)
                    self.jumpThrustForce.setMassDependent(False)
                    thrustFN = ForceNode("world-forces")
                    thrustFN.addForce(self.jumpThrustForce)

                    self.objectNP.node().getPhysical(0).addLinearForce(self.jumpThrustForce)

        if self.landGap >= Avatar.LAND_GAP_PERMISSION: self.landed = False

        elif self.landGap > 0: self.landGap += 1

    def applyFriction(self, friction):

        for component, i in enumerate(friction):

            self.speed[i] -= component

    def handleCollisionEvent(self, type, event):

        collisionRecipient = event.getIntoNodePath().getName()

        #Jump legality

        #print collisionRecipient

        if type == "in":

            if collisionRecipient.startswith("Ground"):

                self.landed = True

                self.landGap = 0

            if collisionRecipient in Asteroid.collisionNames:

                self.alive = False

        elif type == "out" and collisionRecipient.startswith("Ground"):

            self.landGap = 1

class ModelReference(object):

    def __init__(self, modelPath, radialScale, collisionName):

        self.modelPath = modelPath
        self.radialScale = radialScale
        self.collisionName = collisionName

class Asteroid(GameObject):

    COLLISION_NAMES = []

    ASTEROID_MODELS = [ModelReference("models/Asteroid_2", .66),
                       ModelReference("models/Asteroid_2", .66)]

    def __init__(self, objectNP, position, deviationMag, transMag, spinMag):

        GameObject.__init__(self, objectNP)

        self.objectNP.setPos(position[0] + deviationMag*random()*choice([-1,1]), 
                             position[1] + deviationMag*random()*choice([-1,1]), 
                             position[2] + deviationMag*random()*choice([-1,1]))

        self.objectNP.setHpr(360*random(), 360*random(), 360*random())

        self.transSpeed = Vec3(transMag*random(), transMag*random(), transMag*random())
        #self.rotSpeed = Vec3(spinMag*random(), spinMag*random(), spinMag*random())

    def rotate(self):

        pass

        #self.objectNP.setHpr(self.objectNP, self.rotSpeed[0], 
        #            self.rotSpeed[0], self.rotSpeed[0])

    def move(self, avatarSpeed, dt):

        #Relative to universal coordinate system

        self.objectNP.setPos(self.objectNP.getX() + (self.transSpeed[0] + avatarSpeed[0])*dt, 
                             self.objectNP.getY() + (self.transSpeed[1] + avatarSpeed[1])*dt,
                             self.objectNP.getZ() + (self.transSpeed[2] + avatarSpeed[2])*dt)

        self.rotate()

class AsteroidManager(object):

    def __init__(self):

        self.axis_index_dic = {"X" : 0, "Y" : 1, "Z" : 2}

        self.axis_control_dic = {"X" : (lambda x: x.objectNP.getX(), lambda x: x.objectNP.setX),
                        "Y" : (lambda x: x.objectNP.getY(), lambda x: x.objectNP.setY),
                        "Z" : (lambda x: x.objectNP.getZ(), lambda x: x.objectNP.setZ)}

        self.asteroids = []

        self.debug = []

    def initialize(self, level):

        breadth_bound, depth_bound, height_bound = 10, 28, 15

        self.field_expanse = ((-breadth_bound, breadth_bound), (0, depth_bound), 
                              (-height_bound, height_bound))

        difficulty_factor = 1.0 / (log(level))

        self.succession_interval = (int(5 * difficulty_factor), int(5 * difficulty_factor), 
                                    int(5 * difficulty_factor))

        distance = 0

        while distance < self.field_expanse[2][1]:

            self.genSuccession("Y", self.field_expanse[self.axis_index_dic["Y"]][1])

            distance += self.succession_interval[self.axis_index_dic["Y"]]

    def genSuccession(self, axis, distance, direction=None):

        axis_index = (self.axis_index_dic[axis])
        col_index = (self.axis_index_dic[axis] + 1) % len(self.axis_index_dic)
        row_index = (self.axis_index_dic[axis] + 2) % len(self.axis_index_dic)

        ast_location = []

        for ast_column in range(self.field_expanse[col_index][0], self.field_expanse[col_index][1] + self.succession_interval[col_index], 
                                self.succession_interval[col_index]):

            for ast_row in range(self.field_expanse[row_index][0], self.field_expanse[row_index][1] + self.succession_interval[row_index], 
                                self.succession_interval[row_index]):

                ast_location = [0, 0, 0]

                ast_location[axis_index] = distance
                ast_location[col_index] = ast_column
                ast_location[row_index] = ast_row

                model_ref = choice(Asteroid.ASTEROID_MODELS)

                asteroid = Asteroid(loader.loadModel(model_ref.modelPath), ast_location, 5, 1, .1)

                bound = asteroid.objectNP.getBounds()

                pandaBodySphere = CollisionSphere(bound.getCenter()[0] - asteroid.objectNP.getX(),
                                                   bound.getCenter()[1] - asteroid.objectNP.getY(),
                                                   bound.getCenter()[2] - asteroid.objectNP.getZ(), 
                                                   bound.getRadius()*model_ref.radialScale)

                pandaBodySphereNode = CollisionNode("asteroidSphere")
                pandaBodySphereNode.addSolid(pandaBodySphere)
                pandaBodySphereNode.setFromCollideMask(BitMask32.bit(0))
                pandaBodySphereNode.setIntoCollideMask(BitMask32.allOff())

                pandaBodySphereNodepath = asteroid.objectNP.attachNewNode(pandaBodySphereNode)
                #pandaBodySphereNodepath.show()

                self.asteroids.append(asteroid)

    def inView(self, asteroid, camDist):

        BUFFER = self.succession_interval[0] + 1

        LENS_OFFSET = 4

        if (asteroid.objectNP.getX() < self.field_expanse[0][0] - BUFFER or asteroid.objectNP.getX() > self.field_expanse[0][1] + BUFFER) or \
            asteroid.objectNP.getY() < -camDist + LENS_OFFSET or asteroid.objectNP.getZ() < self.field_expanse[2][0] - BUFFER or \
            (asteroid.objectNP.getZ() < self.field_expanse[2][0] - BUFFER):

            return False

        return True

    def maintainAsteroidField(self, avatarPosition, avatarSpeed, camDist, dt):

        self.asteroids = filter(lambda x: self.inView(x, camDist), self.asteroids)

        for asteroid in self.asteroids: asteroid.move(avatarSpeed, dt)

        #start = clock()

        fieldSize = ((min(self.asteroids, key=self.axis_control_dic["X"][0]), max(self.asteroids, key=self.axis_control_dic["X"][0])),
                     (max(self.asteroids, key=self.axis_control_dic["Y"][0]), ),
                     (min(self.asteroids, key=self.axis_control_dic["Z"][0]), max(self.asteroids, key=self.axis_control_dic["Z"][0])))

        #if len(self.debug) < 300:

            #self.debug.append(clock() - start)

        #else:

            #print sum(self.debug)/100

        for i, axis in enumerate(("X", "Y", "Z")):

            access_func =  self.axis_control_dic[axis][0]

            bound = self.field_expanse[i][0] if avatarSpeed[i] > 0 else self.field_expanse[i][1]

            startPoint = min(map(access_func, fieldSize[i])) if bound < 0 else max(map(access_func, fieldSize[i]))

            spawn_direction = bound/(abs(bound))

            while abs(startPoint) < abs(bound):

                startPoint += spawn_direction*self.succession_interval[i]

                self.genSuccession(axis, startPoint, spawn_direction)

    def __del__(self):

        self.asteroids = []

class Turret(GameObject):

    def __init__(self):

        GameObject.__init__(self)

class Camera(object):

    ROT_RATE = (.4, .25)
    ELEVATION = 6.5
    AVATAR_DIST = 20

    MIN_PITCH_ROT = -20
    MAX_PITCH_ROT = 20

    FLEX_ROT_BOUND = (20, 20)

    def __init__(self, cameraObject):

        self.camObject = cameraObject

        self.pitchRot = 0
 
class GameContainer(ShowBase):

    def __init__(self):

        ShowBase.__init__(self)

        ########## Window configuration #########

        wp = WindowProperties()

        wp.setSize(1024, 860)
        wp.setTitle("")

        self.win.requestProperties(wp)

        ########## Gameplay settings #########

        self.gameMode = {"display" : PLAY, "play" : TERRAIN}

        self.level = 1

        self.mode_initialized = False

        ######### Camera #########

        self.disableMouse()

        self.mainCamera = Camera(self.camera)

        self.mainCamera.camObject.setHpr(0, 0, 0)

        #Trigger game chain

        self.loadLevel(LEVEL)

        ######### Events #########

        self.taskMgr.add(self.gameLoop, "gameLoop", priority = 35)

        self.keys = {"w" : 0, "s" : 0, "a" : 0, "d" : 0, "space" : 0,
                     "escape" : 0}

        self.accept("w", self.setKey, ["w", 1])
        self.accept("w-up", self.setKey, ["w", 0])
        self.accept("s", self.setKey, ["s", 1])
        self.accept("s-up", self.setKey, ["s", 0])
        self.accept("a", self.setKey, ["a", 1])
        self.accept("a-up", self.setKey, ["a", 0])
        self.accept("d", self.setKey, ["d", 1])
        self.accept("d-up", self.setKey, ["d", 0])
        self.accept("space", self.setKey, ["space", 1])
        self.accept("space-up", self.setKey, ["space", 0])
        self.accept("escape", self.setKey, ["escape", 1])
        self.accept("escape-up", self.setKey, ["escape", 0])
        self.accept("wheel_up", self.zoomCamera, [-1])
        self.accept("wheel_down", self.zoomCamera, [1])

        self.accept("window-event", self.handleWindowEvent)

        self.accept("playerGroundRayJumping-in", self.avatar.handleCollisionEvent, ["in"])
        self.accept("playerGroundRayJumping-out", self.avatar.handleCollisionEvent, ["out"])

        ######### GUI #########

        self.gui_elements = []

    def setKey(self, key, value):

        self.keys[key] = value

    def zoomCamera(self, direction):

        Camera.AVATAR_DIST += direction

    def toggleCursor(self, state):

        props = WindowProperties()
        props.setCursorHidden(state) 
        base.win.requestProperties(props)

    def handleWindowEvent(self, window=None):

        wp = window.getProperties()

        self.win_center_x = wp.getXSize() / 2
        self.win_center_y = wp.getYSize() / 2

    def processKeys(self):

        if self.keys["escape"]:

            if self.gameMode["display"] == PLAY:

                self.switchDisplayMode(IN_GAME_MENU)

            elif self.gameMode["display"] == IN_GAME_MENU:

                self.switchDisplayMode(PLAY)

            self.setKey("escape", 0)

    ######### Level specific features #########

    def maintainTurrets(self):

        pass

    def switchDisplayMode(self, newGameMode):

        self.cleanupGUI()

        elif self.gameMode["display"] == MAIN_MENU:

            pass

        elif self.gameMode["display"] == IN_GAME_MENU: 

            if newGameMode == PLAY:

                render.clearFog()

            elif newGameMode == MAIN_MENU:

                pass

        elif self.gameMode["display"] == PLAY:

            pass

        self.gameMode["display"] = newGameMode

        self.mode_initialized = False

    def advanceLevel(self):

        self.level += .5

        self.loadLevel()

    def evenButtonPositions(self, button_spacing, button_height, num_buttons):

        center_offset = (button_spacing/(2.0) if (num_buttons % 2 == 0) else 0)

        button_positions = []

        current_pos = center_offset + ((num_buttons - 1)/2) * button_spacing

        for i in range(0, num_buttons):

            button_positions.append(current_pos + (button_height/2.0))

            current_pos -= button_spacing

        return button_positions

    def buildInGameMenu(self):

        props = WindowProperties()
        props.setCursorHidden(False) 
        base.win.requestProperties(props)

        resume_button = DirectButton(text = "Resume", scale = .1, command = (lambda: self.switchDisplayMode(PLAY)), rolloverSound=None)
        main_menu_button = DirectButton(text = "Main Menu", scale = .1, command = None, rolloverSound=None)
        options_button = DirectButton(text = "Settings", scale = .1, command = None, rolloverSound=None)
        exit_button = DirectButton(text = "Exit", scale = .1, command = exit, rolloverSound=None)

        BUTTON_SPACING = .2
        BUTTON_HEIGHT = resume_button.getSy()

        button_positions = self.evenButtonPositions(BUTTON_SPACING, BUTTON_HEIGHT, 4)

        resume_button.setPos(Vec3(0, 0, button_positions[0]))
        main_menu_button.setPos(Vec3(0, 0, button_positions[1]))
        options_button.setPos(Vec3(0, 0, button_positions[2]))
        exit_button.setPos(Vec3(0, 0, button_positions[3]))

        self.gui_elements.append(resume_button)
        self.gui_elements.append(main_menu_button)
        self.gui_elements.append(options_button)
        self.gui_elements.append(exit_button)

    def buildMainMenu(self):

        props = WindowProperties()
        props.setCursorHidden(False) 
        base.win.requestProperties(props)

        start_game_button = DirectButton(text = "Start", scale = .1, command = None)
        select_level_button = DirectButton(text = "Select Level", scale = .1, command = None)
        game_options_button = DirectButton(text = "Settings", scale = .1, command = None)
        exit_button = DirectButton(text = "Exit", scale = .1, command = exit)

        BUTTON_SPACING = .2
        BUTTON_HEIGHT = start_game_button.getSy()

        button_positions = self.evenButtonPositions(BUTTON_SPACING, BUTTON_HEIGHT)

        start_game_button.setPos(Vec3(0, 0, button_positions[0]))
        select_level_button.setPos(Vec3(0, 0, button_positions[1]))
        game_options_button.setPos(Vec3(0, 0, button_positions[2]))
        exit_button.setPos(Vec3(0, 0, button_positions[3]))

        self.gui_elements.append(start_game_button)
        self.gui_elements.append(select_level_button)
        self.gui_elements.append(game_options_button)
        self.gui_elements.append(exit_button)

    def cleanupGUI(self):

        for gui_element in self.gui_elements:

            gui_element.destroy()

    def loadSpaceTexture(self, level):

        if level < 10: return 'textures/space#.jpg'
        elif level < 15: pass  

    def loadLevel(self):

        #Resets

        self.avatarActor = Actor("models/panda",
                                {"walk": "models/panda-walk"})
        self.avatarActor.setScale(.5, .5, .5)
        self.avatarActor.setHpr(180, 0, 0)
        self.avatarActor.setCollideMask(BitMask32.allOff())

        self.asteroidManager = AsteroidManager()

        self.cTrav = CollisionTraverser()

        #Alternate modes

        if int(self.level) == self.level: self.gameMode["play"] = TERRAIN

        else: self.gameMode["play"] = SPACE

        #Specifics

        if self.gameMode["play"] == SPACE:

            self.avatar = Avatar(self.avatarActor, self.level)
            self.avatar.objectNP.reparentTo(render)

            ########## Sky #########

            cubeMap = loader.loadCubeMap(self.loadSpaceTexture(self.level))
            self.spaceSkyBox = loader.loadModel('models/box')
            self.spaceSkyBox.setScale(100)
            self.spaceSkyBox.setBin('background', 0)
            self.spaceSkyBox.setDepthWrite(0)
            self.spaceSkyBox.setTwoSided(True)
            self.spaceSkyBox.setTexGen(TextureStage.getDefault(), TexGenAttrib.MWorldCubeMap)
            self.spaceSkyBox.setTexture(cubeMap, 1)
            parentNP = render.attachNewNode('parent')
            self.spaceSkyBox.reparentTo(parentNP)
            self.spaceSkyBox.setPos(-self.spaceSkyBox.getSx()/2, -self.spaceSkyBox.getSy()/2, 
                                    -self.spaceSkyBox.getSz()/2)

            ########## Collisions #########

            #self.pandaBodySphere = CollisionSphere(self.avatarActor.getBounds().getCenter(), self.avatarActor.getBounds().getRadius())
            bound = self.avatarActor.getBounds()

            self.pandaBodySphere = CollisionSphere(bound.getCenter()[0]/self.avatar.objectNP.getSx() - self.avatar.objectNP.getX(),
                                                   bound.getCenter()[1]/self.avatar.objectNP.getSx() - self.avatar.objectNP.getY(),
                                                   bound.getCenter()[2]/self.avatar.objectNP.getSx() -  self.avatar.objectNP.getZ(), 5)

            #self.pandaBodySphere.setRadius(bound.getRadius()/self.avatar.objectNP.getSx())
            self.pandaBodySphere.setRadius(bound.getRadius() + 1)

            self.pandaBodySphereNode = CollisionNode("playerBodyRay")
            self.pandaBodySphereNode.addSolid(self.pandaBodySphere)
            self.pandaBodySphereNode.setFromCollideMask(BitMask32.bit(0))
            self.pandaBodySphereNode.setIntoCollideMask(BitMask32.allOff())

            self.pandaBodySphereNodepath = self.avatar.objectNP.attachNewNode(self.pandaBodySphereNode)
            self.pandaBodySphereNodepath.show()

            self.asteroidManager.initialize(self.level)

        elif self.gameMode["play"] == TERRAIN:

            ########## Terrain #########

            #self.environ = loader.loadModel("../mystuff/test.egg")
            self.environ = loader.loadModel("models/environment")
            self.environ.setName("terrain")
            self.environ.reparentTo(render)
            self.environ.setPos(0, 0, 0)
            self.environ.setCollideMask(BitMask32.bit(0))

            ######### Physics #########

            self.enableParticles()

            gravityForce = LinearVectorForce(0, 0, -9.81)
            gravityForce.setMassDependent(False)
            gravityFN = ForceNode("world-forces")
            gravityFN.addForce(gravityForce)
            render.attachNewNode(gravityFN)
            base.physicsMgr.addLinearForce(gravityForce)

            self.avatarPhysicsActorNP = render.attachNewNode(ActorNode("player"))
            self.avatarPhysicsActorNP.node().getPhysicsObject().setMass(50.)
            self.avatarActor.reparentTo(self.avatarPhysicsActorNP)
            base.physicsMgr.attachPhysicalNode(self.avatarPhysicsActorNP.node())

            self.avatarPhysicsActorNP.setPos(15, 10, 5)

            ######### Game objects #########

            self.avatar = Avatar(self.avatarPhysicsActorNP, self.level)

            ######### Collisions #########

            self.pandaBodySphere = CollisionSphere(0, 0, 4, 3)

            self.pandaBodySphereNode = CollisionNode("playerBodyRay")
            self.pandaBodySphereNode.addSolid(self.pandaBodySphere)
            self.pandaBodySphereNode.setFromCollideMask(BitMask32.bit(0))
            self.pandaBodySphereNode.setIntoCollideMask(BitMask32.allOff())

            self.pandaBodySphereNodepath = self.avatar.objectNP.attachNewNode(self.pandaBodySphereNode)
            self.pandaBodySphereNodepath.show()

            self.pandaBodyCollisionHandler = PhysicsCollisionHandler()
            self.pandaBodyCollisionHandler.addCollider(self.pandaBodySphereNodepath, self.avatar.objectNP)

            #Keep player on ground

            self.pandaGroundSphere = CollisionSphere(0, 0, 1, 1)

            self.pandaGroundSphereNode = CollisionNode("playerGroundRay")
            self.pandaGroundSphereNode.addSolid(self.pandaGroundSphere)
            self.pandaGroundSphereNode.setFromCollideMask(BitMask32.bit(0))
            self.pandaGroundSphereNode.setIntoCollideMask(BitMask32.allOff())

            self.pandaGroundSphereNodepath = self.avatar.objectNP.attachNewNode(self.pandaGroundSphereNode)
            self.pandaGroundSphereNodepath.show()

            self.pandaGroundCollisionHandler = PhysicsCollisionHandler()
            self.pandaGroundCollisionHandler.addCollider(self.pandaGroundSphereNodepath, self.avatar.objectNP)

            #Notify when player lands

            self.pandaGroundRayJumping = CollisionSphere(0, 0, 1, 1)

            self.pandaGroundRayNodeJumping = CollisionNode("playerGroundRayJumping")
            self.pandaGroundRayNodeJumping.addSolid(self.pandaGroundRayJumping)
            self.pandaGroundRayNodeJumping.setFromCollideMask(BitMask32.bit(0))
            self.pandaGroundRayNodeJumping.setIntoCollideMask(BitMask32.allOff())

            self.pandaGroundRayNodepathJumping = self.avatar.objectNP.attachNewNode(self.pandaGroundRayNodeJumping)
            self.pandaGroundRayNodepathJumping.show()

            self.collisionNotifier = CollisionHandlerEvent()
            self.collisionNotifier.addInPattern("%fn-in")
            self.collisionNotifier.addOutPattern("%fn-out")

            self.cTrav.addCollider(self.pandaGroundSphereNodepath, self.pandaGroundCollisionHandler)
            self.cTrav.addCollider(self.pandaGroundRayNodepathJumping, self.collisionNotifier)
            self.cTrav.addCollider(self.pandaBodySphereNodepath, self.pandaBodyCollisionHandler)

    def gameLoop(self, task):

        dt = globalClock.getDt()

        self.processKeys()

        if self.gameMode["display"] == MAIN_MENU:

            if not self.mode_initialized:

                MenuBuilder.buildMainMenu()

                self.mode_initialized = True

        if self.gameMode["display"] == IN_GAME_MENU:

            if not self.mode_initialized:

                #Fog out background

                inGameMenuFogColor = (50, 150, 50)

                inGameMenuFog = Fog("inGameMenuFog")

                inGameMenuFog.setMode(Fog.MExponential)
                inGameMenuFog.setColor(*inGameMenuFogColor)
                inGameMenuFog.setExpDensity(.01)

                render.setFog(inGameMenuFog)

                self.buildInGameMenu()

                self.mode_initialized = True

        if self.gameMode["display"] == PLAY:

            if not self.mode_initialized:

                props = WindowProperties()
                props.setCursorHidden(True) 
                base.win.requestProperties(props)

                self.last_mouse_x = self.win.getPointer(0).getX()
                self.last_mouse_y = self.win.getPointer(0).getY()

                self.mode_initialized = True

            if self.gameMode["play"] == TERRAIN:

                self.maintainTurrets()
                self.avatar.move(dt)

            elif self.gameMode["play"] == SPACE:

                self.asteroidManager.maintainAsteroidField(self.avatar.objectNP.getPos(), 
                            self.avatar.speed, Camera.AVATAR_DIST, dt)

            #Handle keyboard input

            self.avatar.handleKeys(self.keys, self.gameMode["play"])

            ########## Mouse-based viewpoint rotation ##########

            mouse_pos = self.win.getPointer(0)

            current_mouse_x = mouse_pos.getX()
            current_mouse_y = mouse_pos.getY()

            #Side to side

            if self.gameMode["play"] == TERRAIN:

                mouse_shift_x = current_mouse_x - self.last_mouse_x
                self.last_mouse_x = current_mouse_x

                if current_mouse_x < 5 or current_mouse_x >= (self.win_center_x * 1.5):

                    base.win.movePointer(0, self.win_center_x, current_mouse_y)
                    self.last_mouse_x = self.win_center_x

                yaw_shift = -((mouse_shift_x) * Camera.ROT_RATE[0])

                self.avatar.yawRot += yaw_shift

                self.avatar.objectNP.setH(self.avatar.yawRot)

            #Up and down

            mouse_shift_y = current_mouse_y - self.last_mouse_y
            self.last_mouse_y = current_mouse_y

            if current_mouse_y < 5 or current_mouse_y >= (self.win_center_y * 1.5):

                base.win.movePointer(0, current_mouse_x, self.win_center_y)
                self.last_mouse_y = self.win_center_y

            pitch_shift = -((mouse_shift_y) * Camera.ROT_RATE[1])

            self.mainCamera.pitchRot += pitch_shift

            if self.mainCamera.pitchRot > Camera.FLEX_ROT_BOUND[0]:

                self.mainCamera.pitchRot = Camera.FLEX_ROT_BOUND[0]

            elif self.mainCamera.pitchRot < -Camera.FLEX_ROT_BOUND[0]:

                self.mainCamera.pitchRot = -Camera.FLEX_ROT_BOUND[0]

            xy_plane_cam_dist = Camera.AVATAR_DIST

            cam_x_adjust = xy_plane_cam_dist*sin(radians(self.avatar.yawRot))  
            cam_y_adjust = xy_plane_cam_dist*cos(radians(self.avatar.yawRot))
            cam_z_adjust = Camera.ELEVATION

            self.mainCamera.camObject.setH(self.avatar.yawRot)
            self.mainCamera.camObject.setP(self.mainCamera.pitchRot)

            self.mainCamera.camObject.setPos(self.avatar.objectNP.getX() + cam_x_adjust, self.avatar.objectNP.getY() - cam_y_adjust, 
                            self.avatar.objectNP.getZ() + cam_z_adjust)

            #Find collisions

            self.cTrav.traverse(render)

        return Task.cont
 
app = GameContainer()
app.run()