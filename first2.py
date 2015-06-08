from math import pi, sin, cos, radians
 
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from panda3d.core import Point3, BitMask32, Vec3
from panda3d.core import CollisionTraverser,CollisionNode, CollisionHandlerFloor
from panda3d.core import CollisionSphere, CollisionRay
from panda3d.core import GeoMipTerrain
from panda3d.physics import *
from pandac.PandaModules import WindowProperties

class Asteroid(object):

    def __init__(self):

        pass

class PlayerVessel(object):

    def __init__(self, modelNodePath, initialSpeed):

        self.modelNodePath = modelNodePath

        self.speed = initialSpeed

    def move(self, dt):

        self.modelNodePath.setPos(self.modelNodePath,
            self.speed[0]*dt, self.speed[1]*dt,
            self.speed[2]*dt)

    def getModelNodePath(self):

        return self.modelNodePath

    def getCollisionSphere(self):

        return None

class Camera(object):

    def __init__(self):

        pass
 
class MyApp(ShowBase):

    def __init__(self):

        ShowBase.__init__(self)

        ################
        #Terrain
        ################

        #######
        #self.environ = GeoMipTerrain("terrain")
        #self.environ.setHeightfield("../terrain/first.png")
        #self.environ.setColorMap("../terrain/first-c.png")
        #self.environ.generate()
        #self.environ.getRoot().setScale(1, 1, 100)
        #self.environ.getRoot().setPos(0, 0, 0)
        #self.environ.getRoot().reparentTo(render)
        #self.environ.getRoot().setName("terrain")
        #self.environ.getRoot().setCollideMask(BitMask32.bit(0))
        #######


        self.environ = loader.loadModel("models/environment")
        self.environ.setScale(.25, .25, .25)
        self.environ.reparentTo(render)
        self.environ.setCollideMask(BitMask32.bit(0))

        ################
        #Game objects 
        ################

        self.pandaActor = Actor("models/panda",
                                {"walk": "models/panda-walk"})
        self.pandaActor.setScale(.5, .5, .5)
        self.pandaActor.setHpr(180, 0, 0)
        #self.pandaActor.setPos(50, 50, 50)
        self.pandaActor.setPythonTag("moving", False)
        self.pandaActor.setCollideMask(BitMask32.allOff())
        self.avatarYawRot = 0
        self.avatarPitchRot = 0

        #self.teapot = loader.loadModel("models/teapot")
        #self.teapot.setScale(1, 1, 1)
        #self.teapot.setPos(60, 60, 50)
        #self.teapot.reparentTo(render)

        self.last_mouse_y = self.win.getPointer(0).getY()

        ################
        #Physics
        ################


        base.enableParticles()

        self.avatarNP=base.render.attachNewNode(ActorNode("actor"))
        # Sets up the mass. Note that in this scenario, mass is not taken into consideration.
        self.avatarNP.node().getPhysicsObject().setMass(100.)
        self.avatarNP.setPos(0,0,0)
        # Parent our avatar to the ready to go physics node
        self.pandaActor.reparentTo(self.avatarNP)

        gravityFN=ForceNode('world-forces')
        gravityFNP=render.attachNewNode(gravityFN)
        gravityForce=LinearVectorForce(0,0,-.1)
        gravityForce.setMassDependent(False)
        gravityFN.addForce(gravityForce)
        # Attach it to the global physics manager
        base.physicsMgr.addLinearForce(gravityForce)

        base.physicsMgr.attachPhysicalNode(self.avatarNP.node())

        ################
        #Collisions
        ################

        self.cTrav = CollisionTraverser()
        self.cTrav.showCollisions(base.render)

        self.pandaGroundRay = CollisionSphere(0,0,0,1)
        self.pandaGroundRayNode = CollisionNode('pandaGroundRay')
        self.pandaGroundRayNode.addSolid(self.pandaGroundRay)
        self.pandaGroundRayNode.setFromCollideMask(BitMask32.bit(0))
        self.pandaGroundRayNode.setIntoCollideMask(BitMask32.allOff())
        self.pandaGroundRayNodepath = self.avatarNP.attachNewNode(self.pandaGroundRayNode)
        self.pandaGroundRayNodepath.show()
        self.pandaGroundCollisionHandler = PhysicsCollisionHandler()
        self.pandaGroundCollisionHandler.addCollider(self.pandaGroundRayNodepath, self.avatarNP)
        self.cTrav.addCollider(self.pandaGroundRayNodepath, self.pandaGroundCollisionHandler)

        #self.teapotRay = CollisionSphere(0,0,0,5)
        #self.teapotGroundCol = CollisionNode('teapotRay')
        #self.teapotGroundCol.addSolid(self.teapotRay)
        #self.teapotGroundCol.setFromCollideMask(BitMask32.allOff())
        #self.teapotGroundCol.setIntoCollideMask(BitMask32.bit(0))
        #self.teapotGroundColNp = self.teapot.attachNewNode(self.teapotGroundCol)
        #self.teapotGroundHandler = CollisionHandlerQueue()
        #self.cTrav.addCollider(self.teapotGroundColNp, self.teapotGroundHandler)

        ################
        #Camera
        ################

        self.disableMouse()

        self.cam_away = 20
        self.cam_elevation = 0
        self.rot_rate = .5

        self.cam_dist = (self.cam_away**2 + self.cam_elevation**2) ** .5

        self.cam.setHpr(0, 0, 0)

        ################
        #Events
        ################

        self.taskMgr.add(self.gameLoop, "gameLoop", priority = 35)

        self.keys = {"w" : 0, "s" : 0, "a" : 0, "d" : 0}

        self.accept("w", self.setKey, ["w", 1])
        self.accept("w-up", self.setKey, ["w", 0])
        self.accept("s", self.setKey, ["s", 1])
        self.accept("s-up", self.setKey, ["s", 0])
        self.accept("a", self.setKey, ["a", 1])
        self.accept("a-up", self.setKey, ["a", 0])
        self.accept("d", self.setKey, ["d", 1])
        self.accept("d-up", self.setKey, ["d", 0])
        self.accept("wheel_up", self.zoomCamera, [-1])
        self.accept("wheel_down", self.zoomCamera, [1])

        self.accept('window-event', self.handleWindowEvent)

        props = WindowProperties()
        props.setCursorHidden(True) 
        base.win.requestProperties(props)

        self.last_mouse_x = self.win.getPointer(0).getX()

    def setKey(self, key, value):

        self.keys[key] = value

    def handleWindowEvent(self, window=None):

        wp = window.getProperties()

        self.win_center_x = wp.getXSize() / 2
        self.win_center_y = wp.getYSize() / 2

    def zoomCamera(self, direction):

        self.cam_away += direction

    def gameLoop(self, task):

        dt = globalClock.getDt()

        #self.avatarNP.setY(self.avatarNP, 10 * dt)

        if self.keys["w"]: self.avatarNP.setZ(self.avatarNP, 5 * dt)

        if self.keys["s"]: self.avatarNP.setZ(self.avatarNP, -5 * dt)

        if self.keys["a"]: self.avatarNP.setX(self.avatarNP, -5 * dt)

        if self.keys["d"]: self.avatarNP.setX(self.avatarNP, 5 * dt)

        #Mouse-based viewpoint rotation

        mouse_pos = self.win.getPointer(0)

        current_mouse_x = mouse_pos.getX()
        current_mouse_y = mouse_pos.getY()

        mouse_shift_x = current_mouse_x - self.last_mouse_x
        mouse_shift_y = current_mouse_y - self.last_mouse_y

        self.last_mouse_x = current_mouse_x
        self.last_mouse_y = current_mouse_y

        if current_mouse_x == 0 or current_mouse_x >= (self.win_center_x * 1.5):

            base.win.movePointer(0, self.win_center_x, self.win_center_y)
            self.last_mouse_x = self.win_center_x

        if current_mouse_y == 0 or current_mouse_y >= (self.win_center_y * 1.5):

            base.win.movePointer(0, self.win_center_x, self.win_center_y)
            self.last_mouse_y = self.win_center_y

        #self.cam.setP(0)

        yaw_shift = -((mouse_shift_x) * self.rot_rate)
        pitch_shift = -((mouse_shift_y) * self.rot_rate)

        self.avatarYawRot += yaw_shift
        self.avatarPitchRot += pitch_shift

        self.avatarNP.setH(self.avatarYawRot)
        self.cam.setH(self.avatarYawRot)
        self.cam.setP(-self.avatarPitchRot)

        xy_plane_cam_dist = self.cam_away*cos(radians(self.avatarPitchRot))

        cam_x_adjust = xy_plane_cam_dist*sin(radians(self.avatarYawRot))  
        cam_y_adjust = xy_plane_cam_dist*cos(radians(self.avatarYawRot))
        cam_z_adjust = self.cam_away*sin(radians(self.avatarPitchRot))

        print self.camera.getPos()
        self.cam.setPos(self.avatarNP.getX() + cam_x_adjust, self.avatarNP.getY() - cam_y_adjust, 
                        self.avatarNP.getZ() + cam_z_adjust)

        print self.avatarNP.getPos()

        #self.cam.setP(self.x)
        #self.x += .01

        #self.cTrav.traverse(render)

        #entries = []

        #for i in range(self.pandaGroundCollisionHandler.getNumEntries()):

        #    entry = self.pandaGroundCollisionHandler.getEntry(i)
        #    entries.append(entry)

        #for entry in entries:

        #    print entry.getIntoNode().getName()

        #    if entry.getIntoNode().getName() == "terrain":

        #        print "shiet"

        #        self.pandaActor.setZ(entry.getSurfacePoint(render).getZ())

        return Task.cont
 
app = MyApp()
app.run()