# by FenrirWolf (David Grace) 7/2009
# Free for use by all under the Panda license

# Purpose: Demonstrates how to use Panda physics with a collisions to generate spheres which bounce on a ground
# plane.

from pandac.PandaModules import loadPrcFileData

loadPrcFileData('', '''
show-frame-rate-meter #t
//want-tk #t
//want-directtools #t''')

from pandac.PandaModules import *  # lazy git
import direct.directbase.DirectStart

from random import random

# Set up the collision traverser.  If we bind it to base.cTrav, then Panda will handle
# management of this traverser (for example, by calling traverse() automatically for us once per frame)
base.cTrav = CollisionTraverser()

# Turn on particles.  (Required to use Panda physics)
base.enableParticles()

# Turn on the traverser debugger if you want to see the collisions
#base.cTrav.showCollisions (base.render)

# Having trouble figuring out what's going on with messages?  Turn this on.
#messenger.toggleVerbose()

# Now let's set up some collision bits for our masks
groundBit = 1 
smileyBit = 2

# First, we build a card to represent the ground
cm = CardMaker('ground-card')
cm.setFrame(-60, 60, -60, 60)
card = render.attachNewNode(cm.generate())
card.lookAt (0, 0, -1)  # align upright
tex = loader.loadTexture('maps/envir-ground.jpg')
card.setTexture(tex)

# Then we build a collisionNode which has a plane solid which will be the ground's collision
# representation
groundColNode = card.attachNewNode (CollisionNode('ground-cnode'))
groundColPlane = CollisionPlane (Plane (Vec3(0, -1, 0), Point3(0, 0, 0)))
groundColNode.node().addSolid (groundColPlane)

# Now, set the ground to the ground mask
groundColNode.setCollideMask (BitMask32().bit (groundBit))

# Why aren't we adding a collider?  There is no need to tell the collision traverser about this
# collisionNode, as it will automatically be an Into object during traversal.

# We're going to keep a list of our smileyActorNodes
smileyActors = []

# How many smileys?
maxSmileys = 25

# Our smiley base mass, roughly in kg
baseMass = 100.0

# Let's have some fun and have a PLOP! sound ready for our collisions!
plopSfx = loader.loadSfx ('audio/sfx/GUI_click.wav')

# Create a shadow card for us to use with the smileys
cm = CardMaker ('shadow-card')
cm.setFrame (-1, 1, -1, 1)
shadowCard = render.attachNewNode (cm.generate())
shadowCard.lookAt (0, 0, -1) # align upright
tex = loader.loadTexture ('maps/soft_iris.rgb')
ts = TextureStage ('blended-shadow')

# Using a little trick here...  Since the only thing resembling a shadow blob kind of texture is the
# soft_iris image that comes with Panda.  Problem is, it's opposite of what we want (ie: ring vs blob)
# So we just invert the alpha values stored in this texture and now it's a blob
ts.setCombineAlpha (TextureStage.CMModulate, TextureStage.CSPrevious, TextureStage.COSrcAlpha,
                              TextureStage.CSTexture, TextureStage.COOneMinusSrcAlpha)
shadowCard.setTexture (ts, tex)
shadowCard.setTransparency(TransparencyAttrib.MAlpha)


def removeForce (smileyActor, task):
  '''Removes a temporary nudge force applied to the smiley'''
  
  smileyActor.node().getPhysical(0).removeLinearForce (nudgeForce)  
  return (task.done)

# -- end def removeForce


def groundCollisionEventCallback(entry):
   '''This is our ground collision message handler.  It is called whenever a collision message is triggered'''
   
   # Get our parent actornode
   smileyActor = entry.getFromNodePath().getParent()
   # Why do we call getParent?  Because we are passed the CollisionNode during the event and the
   # ActorNode is one level up from there.  Our node graph looks like so:
   # - ActorNode
   #   + ModelNode
   #   + CollisionNode
   
   # Apply the nudge force to bounce us upwards
   smileyActor.node().getPhysical(0).addLinearForce (nudgeForce)
   
   # set a task that will clear this force a short moment later
   base.taskMgr.doMethodLater (0.1, removeForce, 'removeForceTask', extraArgs=[smileyActor], appendTask=True)
   
   # PLOP!
   plopSfx.play()

# -- end def groundCollisionHandler


def updateShadow (gShadow, i, task):
   '''Updates the shadow cards that are under each smiley'''
   
   gShadow.setPos (smileyActors[i].getX(), smileyActors[i].getY(), 0.1)
   
   # Shadows range from 0-30 units on Z axis.  Above that, they get clamped to certain minimum size
   # Unrealistic, but means you never lose your visual cue
   dist = 1.0 - smileyActors[i].getZ() / 30.0
   z = max (0.25, dist)
   z = min (z, 0.9)
   gShadow.setScale (1.0 * z)
   gShadow.setColor (0, 0, 0, z)
      
   return (task.cont)
# -- end def updateShadow


# Tell the messenger system we're listening for smiley-into-ground messages and invoke our callback
base.accept ('smiley-cnode-into-ground-cnode', groundCollisionEventCallback)

for i in range (0, maxSmileys):
   # Create our smiley's physics node
   smileyActor = render.attachNewNode (ActorNode("SmileyActorNode"))
   
   # Load the good ole smiley face model
   smiley = loader.loadModel('smiley')
   smiley.reparentTo (smileyActor)
   
   # Position the smiley faces randomly in the air
   smileyActor.setPos(random() * 30 - 15, random() * 30 - 15, 100)
   
   # Associate the default PhysicsManager for this ActorNode
   base.physicsMgr.attachPhysicalNode (smileyActor.node())
   
   # Let's set some default body parameters such as mass, and randomize our mass a bit
   smileyActor.node().getPhysicsObject().setMass(baseMass + (baseMass * 0.5) * random())
      
   # Build a collisionNode for this smiley which is a sphere of the same diameter as the model
   smileyColNode = smileyActor.attachNewNode (CollisionNode ('smiley-cnode'))
   smileyColSphere = CollisionSphere (0, 0, 0, 1)
   smileyColNode.node().addSolid (smileyColSphere)
   
   # Watch for collisions with our brothers, so we'll push out of each other
   smileyColNode.node().setIntoCollideMask (BitMask32().bit (smileyBit))
   
   # we're only interested in colliding with the ground and other smileys
   cMask = BitMask32()
   cMask.setBit (groundBit)
   cMask.setBit (smileyBit)
   smileyColNode.node().setFromCollideMask (cMask)
   
   # Now, to keep the spheres out of the ground plane and each other, let's attach a physics handler to them
   smileyHandler = PhysicsCollisionHandler()
   
   # Set the physics handler to manipulate the smiley actor's transform.
   smileyHandler.addCollider (smileyColNode, smileyActor)
   
   # This call adds the physics handler to the traverser list
   # (not related to last call to addCollider!)
   base.cTrav.addCollider (smileyColNode, smileyHandler)
   
   # Now, let's set the collision handler so that it will also do a CollisionHandlerEvent callback
   # But...wait?  Aren't we using a PhysicsCollisionHandler?
   # The reason why we can get away with this is that all CollisionHandlerXs are inherited from CollisionHandlerEvent,
   # so all the pattern-matching event handling works, too
   smileyHandler.addInPattern ('%fn-into-%in')
   
   # Now, add a shadowCard instance to this smiley
   gShadow = render.attachNewNode ('shadownode')
   gShadow.setPos (smileyActor.getX(), smileyActor.getY(), 0.1)
   shadowCard.instanceTo (gShadow)
   gShadow.show()
   # Start updating the shadow
   base.taskMgr.add (updateShadow, 'updateShadowTask', extraArgs=[gShadow, i], appendTask=True)
   
   # Add it to our tracking list
   smileyActors.append (smileyActor)
   
# -- end if   


# Now, let's push the smileys downwards so they will impact the ground plane.  We do so by building
# a physics force pusher that will act as constant gravity.  This is always active.
gravity = ForceNode ('globalGravityForce')
gravityNP = render.attachNewNode (gravity)
gravityForce = LinearVectorForce (0, 0, -9.8)  # 9.8 m/s gravity
gravityForce.setMassDependent (False)  # constant acceleration (set true if you think Galileo was wrong)
gravity.addForce (gravityForce)
# add it to the built-in physics manager
base.physicsMgr.addLinearForce (gravityForce)

# Let's build a world-based temporary pushing force
nudge = ForceNode ('globalNudgeForce')
nudgeNP = render.attachNewNode (nudge)
nudgeForce = LinearVectorForce (0, 0, baseMass * 150.0)  # a sizeable push up into the air
nudgeForce.setMassDependent (True)
nudge.addForce (nudgeForce)
   
# now, position the camera in a sane spot
base.disableMouse()
base.camera.setPos (-50, -50, 50)
base.camera.lookAt (0, 0, 0)

# doo eet
run()