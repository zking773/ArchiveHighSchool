''' 
strike SPACE to put the panda in the air
'''
# Panda imports
import direct.directbase.DirectStart
from direct.showbase.DirectObject import DirectObject
from pandac.PandaModules import *
#
from direct.actor.Actor import Actor
from direct.task import Task

from pandac.PandaModules import PhysicsCollisionHandler

class terra_physics(DirectObject):
  '''a simple physics environment with terrain and an avatar
  '''
  def __init__(self, theavatar, floor, walls=None):
    # Enables the built-in physics
    base.enableParticles()

    avatar=theavatar
    # This is needed so we don't calculate collisions on the actual model,
    # but on the collision node we will add later
    avatar.setCollideMask(BitMask32.allOff())
    # Whenever we want to inter-act with anything to do with collisions/physics,
    # we want to use the actor node path
    self.avatarNP=render.attachNewNode(ActorNode("actor"))
    # Sets up the mass. Note that in this scenario, mass is not taken into consideration.
    self.avatarNP.node().getPhysicsObject().setMass(100.)
    # Parent our avatar to the ready to go physics node
    avatar.reparentTo(self.avatarNP)

    # Set up the gravity force
    gravityFN=ForceNode('world-forces')
    gravityFNP=render.attachNewNode(gravityFN)
    gravityForce=LinearVectorForce(0,0,-9.81)
    gravityForce.setMassDependent(False)
    gravityFN.addForce(gravityForce)
    # Attach it to the global physics manager
    base.physicsMgr.addLinearForce(gravityForce)

    # Set the collision traverser
    base.cTrav = CollisionTraverser( )
    base.cTrav.showCollisions(base.render)
    #define 2 masks, one for the floor contacts between the avatar model and the collision surfaces
    mask_floor = BitMask32.bit(1)
    mask_walls = BitMask32.bit(2)

    # Assign the floor collsion mask to the floor model and hide it
    self.floor = floor
    self.floor.setCollideMask(mask_floor)
    self.floor.hide()

    # the fromObject is our collision information. The documentation for Panda3d
    # recommends that we use a sphere to handle collisions.
    fromObject = self.avatarNP.attachNewNode(CollisionNode("agentCollisionNode"))
    fromObject.node().addSolid(CollisionSphere(0, 0, 2.5, 2.5))
    # We want to handle any sort of collision that happens to us, but not
    # vice-versa
    fromObject.node().setFromCollideMask(mask_floor)
    fromObject.node().setIntoCollideMask(BitMask32.allOff())
    # show the collision shpere
    fromObject.show()

    # Create a collision handler to handle all the physics
    pusher = PhysicsCollisionHandler()
    # attach it our collision node along with our actor node
    pusher.addCollider(fromObject, self.avatarNP)
    # Add the handler to the main collision traverser
    base.cTrav.addCollider(fromObject, pusher)

    # Tell the global physicsMgr about our actor node
    base.physicsMgr.attachPhysicalNode(self.avatarNP.node())
    #
    self.avatarNP.setZ(.2)
#=====================================================================
#
class World(DirectObject):
  #------------------------------------------------------
  #
  def __init__(self):
    #
    self.setup_scene()
    #
    self.showtime()
  #------------------------------------------------------
  #
  def showtime(self):
    '''relevant code for the sample
    '''
    self.actor = Actor("panda", {"walk":"panda-walk"})
    self.actor.setScale(.5, .5, .5)

    terra=loader.loadModel( 'environment' )
    terra.reparentTo( base.render )
    terra.setScale(3)
    #
    floor = loader.loadModel( 'environment' )
    floor.reparentTo( base.render )
    floor.setScale(3)
    floor.hide()
    
    #** here is where the physics happens
    self.phy=terra_physics(self.actor, floor, None)

    self.accept("space", lambda x=50: self.phy.avatarNP.setZ(x))

    base.mouseInterfaceNode.setPos(-150, 30, 5)
    base.taskMgr.add(self.localtask, 'localtask' )
  #--------------------------------------------------------------
  #
  def localtask(self, task):
    base.camera.lookAt(self.actor)
    return Task.cont
  #------------------------------------------------------
  #
  def setup_scene(self):
    # *** Setup lighting
    lightLevel=0.8
    lightPos=(0.0,-10.0,10.0)
    lightHpr=(0.0,-26.0,0.0)
    dlight = DirectionalLight('dlight')
    dlight.setColor(VBase4(lightLevel, lightLevel, lightLevel, 1))
    dlnp = render.attachNewNode(dlight.upcastToPandaNode())
    dlnp.setHpr(lightHpr[0],lightHpr[1],lightHpr[2])
    dlnp.setPos(lightPos[0],lightPos[1],lightPos[2])
    render.setLight(dlnp)

    alight = AmbientLight('alight')
    alight.setColor(VBase4(0.2, 0.2, 0.2, 1))

    # *** Setup scene
    base.setBackgroundColor(0.0,0.1,0.7,1.0)
    base.mouseInterfaceNode.setPos(3.9, 37.26, 3.8)
    base.mouseInterfaceNode.setHpr(-4.5, 35.4, 0.97)

    base.setFrameRateMeter(True)
#-------------------------------------------------------
w=World()
if __name__ == "__main__":
  run()