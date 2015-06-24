from math import pi, sin, cos, radians
from sys import exit
 
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from panda3d.core import Point3, BitMask32, Vec3
from panda3d.core import CollisionTraverser,CollisionNode, CollisionHandlerFloor, CollisionHandlerEvent
from panda3d.core import CollisionSphere, CollisionRay
from panda3d.core import GeoMipTerrain, loadPrcFileData
from panda3d.core import Fog
from panda3d.physics import *
from direct.gui.DirectGui import *
from pandac.PandaModules import WindowProperties

########## Gameplay variables #########

#Game modes

MAIN_MENU = 0
NORMAL = 1
IN_GAME_MENU = 2

#Navigation modes

TERRAIN = 0
SPACE = 1

LEVEL = 1

class Avatar(object):

    max_velocity = (5, 15)
    acceleration = (.1, .5)

    LAND_GAP_PERMISSION = 5

    def __init__(self, objectNP):

        self.objectNP = objectNP

        self.speed = Vec3(0, 0, 0)

        self.yawRot = 0

        #Jumping variables

        self.landed = False
        self.landGap = 0
        self.jumpThrusting = False
        self.jumpThrustCounter = 10

    def move(self, dt):

        #Move around

        self.objectNP.setPos(self.objectNP,
            self.speed[0]*dt, self.speed[1]*dt,
            self.speed[2]*dt)

        #Jump

        if self.jumpThrusting:

            self.landed = False

            if self.jumpThrustCounter < 10:

                self.jumpThrustCounter += 1

            else:

                self.objectNP.node().getPhysical(0).removeLinearForce(self.jumpThrustForce)

                self.jumpThrusting = False

    def handleKeys(self, keys):

        #Navigate

        if keys["w"]: self.speed[1] += Avatar.acceleration[1]

        if keys["s"]: self.speed[1] += -Avatar.acceleration[1] 

        if keys["a"]: self.speed[0] += -Avatar.acceleration[0]

        if keys["d"]: self.speed[0] += Avatar.acceleration[0]

        for i, bound in enumerate(Avatar.max_velocity):

            if self.speed[i] > bound:

                self.speed[i] = bound

        #Jump requests

        if keys["space"]:

            if self.landed:

                if self.jumpThrustCounter == 10 and not self.jumpThrusting:

                    self.landed = False

                    self.jumpThrusting = True
                    self.jumpThrustCounter = 0

                    self.jumpThrustForce = LinearVectorForce(0, 0, 50)
                    self.jumpThrustForce.setMassDependent(False)

                    thrustFN = ForceNode("world-forces")

                    thrustFN.addForce(self.jumpThrustForce)

                    self.objectNP.node().getPhysical(0).addLinearForce(self.jumpThrustForce)

        #Jump legality

        if self.landGap >= Avatar.LAND_GAP_PERMISSION:

            self.landed = False

        elif self.landGap > 0:

            self.landGap += 1

    def applyFriction(self, friction):

        for component, i in enumerate(friction):

            self.speed[i] -= component

    def handleCollisionEvent(self, type, event):

        collisionRecipient = event.getIntoNodePath().getName()

        #Jump legality

        print collisionRecipient

        if type == "in" and collisionRecipient.startswith("Ground"):

            self.landed = True

            print "balls"

            self.landGap = 0

        elif type == "out" and collisionRecipient.startswith("Ground"):

            print "outie!" 

            self.landGap = 1

class Camera(object):

    ROT_RATE = (.4, .25)
    ELEVATION = 6.5
    AVATAR_DIST = 20

    MIN_PITCH_ROT = -20
    MAX_PITCH_ROT = 20

    FLEX_ROT_MAG = (20, 20)

    def __init__(self, cameraObject):

        self.camObject = cameraObject

        self.pitchRot = 0
 
class GameContainer(ShowBase):

    def __init__(self):

        ShowBase.__init__(self)

        ########## Window configuration #########

        wp = WindowProperties()
        wp.setSize(1024, 860)

        self.win.requestProperties(wp)

        ########## Gameplay settings #########

        self.GAME_MODE = NORMAL
        self.NAVIGATION_MODE = SPACE

        self.mode_initialized = False

        #Trigger game chain

        self.loadWorld(LEVEL)

        ######### Camera #########

        self.disableMouse()

        self.mainCamera = Camera(self.camera)

        self.mainCamera.camObject.setHpr(0, 0, 0)

        ######### Events #########

        self.taskMgr.add(self.gameLoop, "gameLoop", priority = 35)

        self.keys = {"w" : 0, "s" : 0, "a" : 0, "d" : 0, "space" : 0}

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
        self.accept("wheel_up", self.zoomCamera, [-1])
        self.accept("wheel_down", self.zoomCamera, [1])
        self.accept("escape", self.switchGameMode, [IN_GAME_MENU])

        self.accept("window-event", self.handleWindowEvent)

        self.accept("playerGroundRayJumping-in", self.avatar.handleCollisionEvent, ["in"])
        self.accept("playerGroundRayJumping-out", self.avatar.handleCollisionEvent, ["out"])

        ######### GUI #########

        self.gui_elements = []

    def loadWorld(self, level):

        self.avatarActor = Actor("models/panda",
                                {"walk": "models/panda-walk"})
        self.avatarActor.setScale(.5, .5, .5)
        self.avatarActor.setHpr(180, 0, 0)
        self.avatarActor.setPythonTag("moving", False)
        self.avatarActor.setCollideMask(BitMask32.allOff())

        if int(level) == level:

            pass

        ########## Terrain #########

        self.environ = loader.loadModel("models/environment")
        self.environ.setName("terrain")
        self.environ.reparentTo(render)
        self.environ.setPos(0, 0, 0)
        self.environ.setCollideMask(BitMask32.bit(0))

        ######### Models #########

        

        ######### Physics #########

        base.enableParticles()

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

        self.avatar = Avatar(self.avatarPhysicsActorNP)

        ######### Collisions #########

        self.cTrav = CollisionTraverser()

        #Make player rigid body

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

    def setKey(self, key, value):

        self.keys[key] = value

    def zoomCamera(self, direction):

        Camera.AVATAR_DIST += direction

    def b(self, hey):

        self.avatarLanded = True

    def handleWindowEvent(self, window=None):

        wp = window.getProperties()

        self.win_center_x = wp.getXSize() / 2
        self.win_center_y = wp.getYSize() / 2

    def switchGameMode(self, newGameMode=None):

        self.cleanupGUI()

        if self.GAME_MODE == IN_GAME_MENU: 

            if newGameMode == NORMAL:

                render.clearFog()

            elif newGameMode == MAIN_MENU:

                print "bubbles!"

        elif True:

            pass

        self.GAME_MODE = newGameMode

        self.mode_initialized = False

    def cleanupGUI(self):

        for gui_element in self.gui_elements:

            gui_element.destroy()

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

        resume_button = DirectButton(text = "Resume", scale = .1, command = (lambda: self.switchGameMode(NORMAL)),
                                    rolloverSound=None)

        main_menu_button = DirectButton(text = "Main Menu", scale = .1, command = self.b,
                                    rolloverSound=None)

        options_button = DirectButton(text = "Options", scale = .1, command = self.b,
                                    rolloverSound=None)

        exit_button = DirectButton(text = "Exit", scale = .1, command = exit,
                                    rolloverSound=None)

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

        start_game_button = DirectButton(text = "Start", scale = .1,
                            command = self.b)

        select_level_button = DirectButton(text = "Select Level", scale = .1,
                            command = self.b)

        game_options_button = DirectButton(text = "Options", scale = .1,
                            command = self.b)

        exit_button = DirectButton(text = "Exit", scale = .1,
                            command = exit)

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

    def gameLoop(self, task):

        #Compensate for inconsistent update intervals

        dt = globalClock.getDt()

        if self.GAME_MODE == MAIN_MENU:

            if not self.mode_initialized:

                self.buildMainMenu()

                self.mode_initialized = True

        if self.GAME_MODE == IN_GAME_MENU:

            #Fog out background

            if not self.mode_initialized:

                inGameMenuFogColor = (50, 150, 50)

                inGameMenuFog = Fog("inGameMenuFog")

                inGameMenuFog.setMode(Fog.MExponential)
                inGameMenuFog.setColor(*inGameMenuFogColor)
                inGameMenuFog.setExpDensity(.01)

                render.setFog(inGameMenuFog)

                self.buildInGameMenu()

                self.mode_initialized = True

        if self.GAME_MODE == NORMAL:

            if not self.mode_initialized:

                props = WindowProperties()
                props.setCursorHidden(True) 
                base.win.requestProperties(props)

                self.last_mouse_x = self.win.getPointer(0).getX()
                self.last_mouse_y = self.win.getPointer(0).getY()

                self.mode_initialized = True

            if self.NAVIGATION_MODE == TERRAIN:

                pass

            elif self.NAVIGATION_MODE == SPACE:

                pass

            #Handle keyboard input

            self.avatar.handleKeys(self.keys)
            self.avatar.move(dt)

            ########## Mouse-based viewpoint rotation ##########

            mouse_pos = self.win.getPointer(0)

            current_mouse_x = mouse_pos.getX()
            current_mouse_y = mouse_pos.getY()

            mouse_shift_x = current_mouse_x - self.last_mouse_x
            mouse_shift_y = current_mouse_y - self.last_mouse_y

            self.last_mouse_x = current_mouse_x
            self.last_mouse_y = current_mouse_y

            if current_mouse_x < 5 or current_mouse_x >= (self.win_center_x * 1.5):

                base.win.movePointer(0, self.win_center_x, current_mouse_y)
                self.last_mouse_x = self.win_center_x

            if current_mouse_y < 5 or current_mouse_y >= (self.win_center_y * 1.5):

                base.win.movePointer(0, current_mouse_x, self.win_center_y)
                self.last_mouse_y = self.win_center_y

            yaw_shift = -((mouse_shift_x) * Camera.ROT_RATE[0])
            pitch_shift = -((mouse_shift_y) * Camera.ROT_RATE[1])

            self.avatar.yawRot += yaw_shift
            self.mainCamera.pitchRot += pitch_shift

            if self.mainCamera.pitchRot > Camera.FLEX_ROT_MAG[0]:

                self.mainCamera.pitchRot = Camera.FLEX_ROT_MAG[0]

            elif self.mainCamera.pitchRot < -Camera.FLEX_ROT_MAG[0]:

                self.mainCamera.pitchRot = -Camera.FLEX_ROT_MAG[0]

            xy_plane_cam_dist = Camera.AVATAR_DIST

            cam_x_adjust = xy_plane_cam_dist*sin(radians(self.avatar.yawRot))  
            cam_y_adjust = xy_plane_cam_dist*cos(radians(self.avatar.yawRot))
            cam_z_adjust = Camera.ELEVATION

            self.avatar.objectNP.setH(self.avatar.yawRot)

            self.mainCamera.camObject.setH(self.avatar.yawRot)
            self.mainCamera.camObject.setP(self.mainCamera.pitchRot)

            self.mainCamera.camObject.setPos(self.avatar.objectNP.getX() + cam_x_adjust, self.avatar.objectNP.getY() - cam_y_adjust, 
                            self.avatar.objectNP.getZ() + cam_z_adjust)

            #Find collisions

            self.cTrav.traverse(render)

        return Task.cont
 
app = GameContainer()
app.run()