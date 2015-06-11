from math import pi, sin, cos, radians
 
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from panda3d.core import Point3, BitMask32, Vec3
from panda3d.core import CollisionTraverser,CollisionNode, CollisionHandlerFloor
from panda3d.core import CollisionHandlerEvent
from panda3d.core import CollisionSphere, CollisionRay
from panda3d.core import GeoMipTerrain, loadPrcFileData
from panda3d.physics import *
from pandac.PandaModules import WindowProperties

########## Gameplay variables #########

#Game modes

MAIN_MENU = 0
NORMAL = 1

GAME_MODE = NORMAL

#Navigation modes

TERRAIN = 0
SPACE = 1

NAVIGATION_MODE = TERRAIN

class PlayerVessel(object):

    def __init__(self, modelNodePath):

        self.modelNodePath = modelNodePath

        self.speed = Vec3(0, 0, 0)

    def move(self, dt):

        self.modelNodePath.setPos(self.modelNodePath,
            self.speed[0]*dt, self.speed[1]*dt,
            self.speed[2]*dt)

    def getCollisionSphere(self):

        return None

    def handleKeys(self, keys):

        return None

    def handleCollisionEvent(self, eventName):

        return None

class Camera(object):

    ROT_RATE = (.5, .25)
    ELEVATION = 5
    AVATAR_DIST = 20

    MIN_PITCH_ROT = -20
    MAX_PITCH_ROT = 20

    def __init__(self):

        pass
 
class MyApp(ShowBase):

    def __init__(self):

        ShowBase.__init__(self)

        wp = WindowProperties()
        wp.setSize(1024, 860)
        self.win.requestProperties(wp)

        ########## Terrain #########

        self.environ = loader.loadModel("models/environment")
        self.environ.setName("terrain")
        #self.environ.setScale(.25, .25, .25)
        self.environ.reparentTo(render)
        self.environ.setCollideMask(BitMask32.bit(0))

        ######### Game objects #########

        self.pandaActor = Actor("models/panda",
                                {"walk": "models/panda-walk"})
        self.pandaActor.setScale(.5, .5, .5)
        self.pandaActor.setHpr(180, 0, 0)
        self.pandaActor.setPythonTag("moving", False)
        self.pandaActor.setCollideMask(BitMask32.allOff())
        self.avatarYawRot = 0
        self.avatarPitchRot = 0
        self.avatarLanded = True
        self.jumpThrusting = False
        self.jumpThrustCounter = 10

        ######### Physics #########

        base.enableParticles()

        self.avatarNP = base.render.attachNewNode(ActorNode("player"))
        self.avatarNP.setName("player")
        self.avatarNP.node().getPhysicsObject().setMass(50.)
        self.avatarNP.setPos(15,10,5)

        self.pandaActor.reparentTo(self.avatarNP)

        gravityFN = ForceNode('world-forces')
        gravityFNP = render.attachNewNode(gravityFN)
        gravityForce = LinearVectorForce(0, 0, -9.81)
        gravityForce.setMassDependent(False)
        gravityFN.addForce(gravityForce)
        # Attach it to the global physics manager
        base.physicsMgr.addLinearForce(gravityForce)

        base.physicsMgr.attachPhysicalNode(self.avatarNP.node())

        ######### Collisions #########

        self.cTrav = CollisionTraverser()
        #self.cTrav.showCollisions(base.render)

        #Make player rigid body

        self.pandaBodySphere = CollisionSphere(0, 0, 4, 3)

        self.pandaBodySphereNode = CollisionNode('playerBodyRay')
        self.pandaBodySphereNode.addSolid(self.pandaBodySphere)
        self.pandaBodySphereNode.setFromCollideMask(BitMask32.bit(0))
        self.pandaBodySphereNode.setIntoCollideMask(BitMask32.allOff())

        self.pandaBodySphereNodepath = self.avatarNP.attachNewNode(self.pandaBodySphereNode)
        self.pandaBodySphereNodepath.show()

        self.pandaBodyCollisionHandler = PhysicsCollisionHandler()
        self.pandaBodyCollisionHandler.addCollider(self.pandaBodySphereNodepath, self.avatarNP)

        #Keep player on ground

        self.pandaGroundSphere = CollisionSphere(0, 0, 1, 1)

        self.pandaGroundSphereNode = CollisionNode('playerGroundRay')
        self.pandaGroundSphereNode.addSolid(self.pandaGroundSphere)
        self.pandaGroundSphereNode.setFromCollideMask(BitMask32.bit(0))
        self.pandaGroundSphereNode.setIntoCollideMask(BitMask32.allOff())

        self.pandaGroundSphereNodepath = self.avatarNP.attachNewNode(self.pandaGroundSphereNode)
        self.pandaGroundSphereNodepath.show()

        self.pandaGroundCollisionHandler = PhysicsCollisionHandler()
        self.pandaGroundCollisionHandler.addCollider(self.pandaGroundSphereNodepath, self.avatarNP)

        #Notify when player lands

        self.pandaGroundRayJumping = CollisionSphere(0, 0, 1, 1)

        self.pandaGroundRayNodeJumping = CollisionNode('playerGroundRayJumping')
        self.pandaGroundRayNodeJumping.addSolid(self.pandaGroundRayJumping)
        self.pandaGroundRayNodeJumping.setFromCollideMask(BitMask32.bit(0))
        self.pandaGroundRayNodeJumping.setIntoCollideMask(BitMask32.allOff())

        self.pandaGroundRayNodepathJumping = self.avatarNP.attachNewNode(self.pandaGroundRayNodeJumping)
        self.pandaGroundRayNodepathJumping.show()

        self.collisionNotifier = CollisionHandlerEvent()
        self.collisionNotifier.addInPattern('%fn-in')
        self.collisionNotifier.addOutPattern('%fn-out')

        self.cTrav.addCollider(self.pandaGroundSphereNodepath, self.pandaGroundCollisionHandler)
        self.cTrav.addCollider(self.pandaGroundRayNodepathJumping, self.collisionNotifier)
        self.cTrav.addCollider(self.pandaBodySphereNodepath, self.pandaBodyCollisionHandler)

        ######### Camera #########

        self.disableMouse()

        self.cam.setHpr(0, 0, 0)

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

        self.accept('window-event', self.handleWindowEvent)

        self.accept('playerGroundRayJumping-in', self.b)

        ######### Mouse #########

        props = WindowProperties()
        props.setCursorHidden(True) 
        base.win.requestProperties(props)

        self.last_mouse_x = self.win.getPointer(0).getX()
        self.last_mouse_y = self.win.getPointer(0).getY()

    def b(self, hey):

        self.avatarLanded = True

        print "fucky"

    def setKey(self, key, value):

        self.keys[key] = value

    def handleWindowEvent(self, window=None):

        wp = window.getProperties()

        self.win_center_x = wp.getXSize() / 2
        self.win_center_y = wp.getYSize() / 2

    def zoomCamera(self, direction):

        Camera.AVATAR_DIST += direction

    def gameLoop(self, task):

        #Compensate for inconsistent update intervals

        dt = globalClock.getDt()

        if GAME_MODE == NORMAL:

            #Handle keyboard input

            if self.keys["w"]: self.avatarNP.setY(self.avatarNP, 5 * dt)

            if self.keys["s"]: self.avatarNP.setY(self.avatarNP, -5 * dt)

            if self.keys["a"]: self.avatarNP.setX(self.avatarNP, -5 * dt)

            if self.keys["d"]: self.avatarNP.setX(self.avatarNP, 5 * dt)

            if self.avatarLanded:

                if self.keys["space"]:

                    if self.jumpThrustCounter == 10 and not self.jumpThrusting:

                        self.avatarLanded = False

                        self.jumpThrusting = True
                        self.jumpThrustCounter = 0

                        thrustFN = ForceNode('world-forces')

                        self.jumpThrustForce = LinearVectorForce(0, 0, 50)
                        self.jumpThrustForce.setMassDependent(False)

                        thrustFN.addForce(self.jumpThrustForce)

                        self.avatarNP.node().getPhysical(0).addLinearForce(self.jumpThrustForce)

            if self.jumpThrusting:

                self.avatarLanded = False

                if self.jumpThrustCounter < 10:

                    self.jumpThrustCounter += 1

                else:

                    self.avatarNP.node().getPhysical(0).removeLinearForce(self.jumpThrustForce)

                    self.jumpThrusting = False

            #Mouse-based viewpoint rotation

            mouse_pos = self.win.getPointer(0)

            current_mouse_x = mouse_pos.getX()
            current_mouse_y = mouse_pos.getY()

            mouse_shift_x = current_mouse_x - self.last_mouse_x
            mouse_shift_y = current_mouse_y - self.last_mouse_y

            self.last_mouse_x = current_mouse_x
            self.last_mouse_y = current_mouse_y

            if current_mouse_x < 5 or current_mouse_x >= (self.win_center_x * 1.5):

                base.win.movePointer(0, self.win_center_x, self.win_center_y)
                self.last_mouse_x = self.win_center_x

            if current_mouse_y < 5 or current_mouse_y >= (self.win_center_y * 1.5):

                base.win.movePointer(0, self.win_center_x, self.win_center_y)
                self.last_mouse_y = self.win_center_y

            yaw_shift = -((mouse_shift_x) * Camera.ROT_RATE[0])
            pitch_shift = -((mouse_shift_y) * Camera.ROT_RATE[1])

            self.avatarYawRot += yaw_shift
            self.avatarPitchRot += pitch_shift

            if self.avatarPitchRot > Camera.MAX_PITCH_ROT:

                self.avatarPitchRot = Camera.MAX_PITCH_ROT

            elif self.avatarPitchRot < Camera.MIN_PITCH_ROT:

                self.avatarPitchRot = Camera.MIN_PITCH_ROT

            self.avatarNP.setH(self.avatarYawRot)

            self.cam.setH(self.avatarYawRot)
            self.cam.setP(self.avatarPitchRot)

            if NAVIGATION_MODE == TERRAIN:

                xy_plane_cam_dist = Camera.AVATAR_DIST

                cam_z_adjust = Camera.ELEVATION

            elif NAVIGATION_MODE == SPACE:

                xy_plane_cam_dist = Camera.AVATAR_DIST*cos(radians(self.avatarPitchRot))
            
                cam_z_adjust = Camera.AVATAR_DIST*sin(radians(self.avatarPitchRot))

            cam_x_adjust = xy_plane_cam_dist*sin(radians(self.avatarYawRot))  
            cam_y_adjust = xy_plane_cam_dist*cos(radians(self.avatarYawRot))

            self.cam.setPos(self.avatarNP.getX() + cam_x_adjust, self.avatarNP.getY() - cam_y_adjust, 
                            self.avatarNP.getZ() + cam_z_adjust)

            self.cTrav.traverse(render)

        return Task.cont
 
app = MyApp()
app.run()