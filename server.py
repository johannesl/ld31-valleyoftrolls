from geventwebsocket import WebSocketServer, WebSocketApplication, Resource
import gevent
from random import randint

import json
import math
import sys

games = []
waiting = []

MOUNTAIN = 0
TROLL    = 1
VILLAGE  = 2
SOLDIER  = 3
EMPTY    = 4

NORTH     = 0
NORTHEAST = 1
SOUTHEAST = 2
SOUTH     = 3
SOUTHWEST = 4
NORTHWEST = 5

#
# GAME LOGIC
#

def dir2txy (direction, tx, ty):

  if direction == NORTH:
    return tx,ty-1

  if direction == NORTHEAST and tx%2 == 0:
    return tx+1,ty
  elif direction == NORTHEAST:
    return tx+1,ty-1

  if direction == SOUTHEAST and tx%2 == 0:
    return tx+1,ty+1
  elif direction == SOUTHEAST:
    return tx+1,ty

  if direction == SOUTH:
    return tx,ty+1

  if direction == SOUTHWEST and tx%2 == 0:
    return tx-1,ty+1
  elif direction == SOUTHWEST:
    return tx-1,ty

  if direction == NORTHWEST and tx%2 == 0:
    return tx-1,ty
  elif direction == NORTHWEST:
    return tx-1,ty-1

print dir2txy(SOUTH, 0, 0)  # 0,1
print dir2txy(NORTHEAST, 0, 0)  # 1,0
print dir2txy(SOUTHEAST, 0, 0)  # 1,1
#sys.exit(0)

class Game:

  def __init__(self):
    self.gamestate = []
    self.clients = []
    self.paused = 0
    self.playersReported = 0
    self.winner = -1

    # FIXME
    self.minplayers = 4
    self.playercount = 0
    self.playersOnline = 0
    self.turn = -1
    
    # Generate a new map

    # Empty map
    for y in range(0,5):
      for x in range(0,7):
        #if x % 2 == 0:
        #  if y >= 4: continue
        
        # Empty tile for now
        self.gamestate.append( {} )

    # Four starting positions
    starts = [
      [(0,0), (1,0), (1,1)],
      [(5,0), (6,0), (5,1)],
      [(0,3), (1,3), (1,4)],
      [(5,3), (6,3), (5,4)]
    ]
    for i in range(0,self.minplayers):
      randint(0,3)
      x,y = starts[i][randint(0,2)]
      self.hometile( self.gamestate[y*7+x], i )

    # The rest of the map
    for y in range(0,5):
      for x in range(0,7):
        if x % 2 == 0:
          if y >= 4: continue
        
        # Random tile contents
        tile = self.gamestate[y*7+x]
        if tile == {}:
          self.randomizetile(tile, x, y)
  
  def randomizetile (self, tile, x, y):
    # Randomize new tile
    i = randint(0,9)
    if i < 5:
      tile['type'] = VILLAGE # Village
    elif i == 6: 
      tile['type'] = MOUNTAIN # Mountain
    elif i == 7:
      if randint(0,1) == 0:
        tile['type'] = EMPTY # Empty
      else:
        tile['type'] = MOUNTAIN
    else:
      tile['type'] = TROLL # Troll

    if i == 9:
      if randint(0,1) == 0:
        tile['type'] = EMPTY # Empty
      else:
        tile['type'] = MOUNTAIN
    elif i == 8 or i == 7 or i == 5:
      tile['type'] = VILLAGE # Village
    elif i == 6: 
      tile['type'] = TROLL # Mountain
    elif i == 4:
      tile['type'] = VILLAGE # Super Village
    else:
      tile['type'] = EMPTY # Troll


    tile['owner'] = 4

    if tile['type'] == 2:
      tile['owner'] = 4
      if i == 4:
        tile['size'] = randint(70,240)
        tile['economy'] = randint(0,5)
        tile['defense'] = randint(0,4)
      else:
        tile['size'] = randint(20,40,)
        tile['economy'] = 0
        tile['defense'] = 0

    #tile['type'] = 4
    tile['orders'] = [0,0,0,0,0,0]
    tile['mode'] = 0
    tile['burning'] = 0
  
  def hometile (self, tile, player):
    tile['type'] = 2
    tile['owner'] = player
    tile['economy'] = 1
    tile['defense'] = 0
    tile['orders'] = [0,0,0,0,0,0]
    tile['size'] = 80
    tile['burning'] = 0

  def startgame (self):
    self.sendstate()
  
  # New turn data from client received
  def addorders (self, player, data):
  
    self.playersReported += 1
  
    for key in data:
      # skip for now
      if key == 'turn': continue

      x,y = key.split(',')
      tx = int(x)
      ty = int(y)
      
      # safety
      if tx < 0 or tx >= 7:
        continue
      if ty < 0 or ty >= 5:
        continue
      if tx % 2 == 0 and ty >= 4:
        continue
      
      mode, orders = data[key]
      print mode,orders

      # Split armies out
      totalweight = 0
      for direction in range(0,len(orders)):
        if orders[direction] > 0:
        
          # Valid direction? FIXME
          dx,dy = dir2txy( direction, tx, ty )
          
          if orders[direction] == 1:
            weight = 1
          else:
            weight = 3
          
          totalweight += weight
      
      print totalweight
      
      tile = self.gamestate[ty*7+tx]
      startsize = tile['size']
      
      for direction in range(0,len(orders)):
        if orders[direction] == 0 or tile['size'] <= 0: continue
      
        dx,dy = dir2txy( direction, tx, ty )
        dtile = self.gamestate[dy*7+dx]
        
        print direction,dx,dy,dtile

        if orders[direction] == 1:
          weight = 1
        else:
          weight = 3

        size = math.ceil( startsize*weight / float(totalweight) )
        if weight == 1 and size > math.ceil(startsize/3):
          size = math.ceil(startsize/3)

        if size > tile['size']:
          size = tile['size']

        print direction, weight, size
        #dtile['type'] = MOUNTAIN

        # Is this soldier leaving?
        tile['size'] -= size
        if tile['type'] == SOLDIER and tile['size'] == 0:
          tile['owner'] = 4
          tile['type'] = EMPTY

        if dtile['owner'] == player:
          if dtile.has_key('supporters'):
            dtile['supporters'] += size
          else:
            dtile['supporters'] = size
        else:
          if not dtile.has_key('attackers'):
            dtile['attackers'] = {}
          
          # Group attackers of the same tribe
          if not dtile['attackers'].has_key(player):
            dtile['attackers'][player] = 0
          dtile['attackers'][player] += size
          
          print dtile['attackers']

    if not self.paused and self.playersReported == self.playersOnline:
      self.newturn()

  def newturn (self):
    self.turn += 1
    self.playersReported = 0

    # Resource boost
    for ty in range(0,5):
      for tx in range(0,7):
        if tx % 2 == 0:
          if ty >= 4: continue
        
        tile = self.gamestate[ty*7+tx]
        if tile['type'] == VILLAGE and tile['owner'] < 4:
          tile['size'] += 4 + tile['economy']

    # Supporters
    for ty in range(0,5):
      for tx in range(0,7):
        if tx % 2 == 0:
          if ty >= 4: continue
          
        tile = self.gamestate[ty*7+tx]
        if tile.has_key('supporters'):
          tile['size'] += tile['supporters']
          del tile['supporters']

    # Attacks?
    for ty in range(0,5):
      for tx in range(0,7):
        if tx % 2 == 0:
          if ty >= 4: continue
          
        tile = self.gamestate[ty*7+tx]
        
        if tile.has_key('attackers'):
          # Internal fight between attackers first (lucky defender)
          # FIXME
            
          player = tile['attackers'].keys()[0]
          size = tile['attackers'][player]

          # Unoccupied?
          if tile['type'] == EMPTY:
            tile['owner'] = player
            tile['size'] = size
            tile['type'] = SOLDIER
          else:
            tile['burning'] = 1 # FIXME

            # Troll
            if tile['type'] == TROLL:
              if size > 40:
                tile['type'] = SOLDIER
                tile['owner'] = player
                tile['size'] = size - 40
                tile['burning'] = 2
            elif tile['type'] == SOLDIER:
              defensebonus = 0.8
            
              if size > math.floor(tile['size']*defensebonus): # Negative defense bonus
                tile['owner'] = player
                tile['size'] = size - math.floor(tile['size']*defensebonus)
                tile['burning'] = 2
              else:
                tile['size'] -= math.ceil( size/defensebonus )
            
            elif tile['type'] == VILLAGE:
            
              # 10% default defense bonus
              defensebonus = 1.1
              
              if tile['defense'] > 0:
                defensebonus += 0.1*tile['defense']
            
              if size > math.floor(tile['size']*defensebonus):
                tile['owner'] = player
                tile['size'] = size - math.floor(tile['size']*defensebonus)
                tile['burning'] = 2
              else:
                tile['size'] -= math.ceil( size/defensebonus )
                
          
            # Enemy village

          del tile['attackers']
          #self.paused = 1

    self.sendstate()
    
    # Clear away burning
    for ty in range(0,5):
      for tx in range(0,7):
        if tx % 2 == 0:
          if ty >= 4: continue
        
        tile = self.gamestate[ty*7+tx]
        
        tile['burning'] = 0
        if tile['type'] != VILLAGE and tile['type'] != SOLDIER:
          tile['owner'] = 4
    
    # Any winner?
    living = {}
    for ty in range(0,5):
      for tx in range(0,7):
        if tx % 2 == 0:
          if ty >= 4: continue
        
        tile = self.gamestate[ty*7+tx]
        if tile['type'] == VILLAGE or tile['type'] == SOLDIER:
          if tile['owner'] < 4:
            living[tile['owner']] = 1

    if self.winner == -1 and len(living) == 1:
      self.winner = living.keys()[0]
      self.sendstate()

    # Grow surviving villages
    pass

  def sendstate (self):
    if self.winner > -1:
      print 'WE HAVE A WINNER', self.winner
      for client in self.clients:
        if client.player == self.winner:
          client.ws.send( '{"win":"youwin"}' )
        else:
          client.ws.send( '{"win":"youloose"}' )
      self.paused = 1

    else:
      # Send out intial gamestate to all players
      for client in self.clients:
        s = json.dumps(self.gamestate)
        client.ws.send( s )
      
  def sendplayercount(self):
    self.playercount = len(self.clients)
  
    if self.playercount == self.minplayers:
      playercount = 4
      self.turn = 0
      self.playersOnline = self.playercount
      self.playersReported = 0
    else:
      playercount = self.playercount
      
    drop = []
    for client in self.clients:
      try:
        client.ws.send( json.dumps({'team':client.player,'playercount':playercount}))
      except:
        drop.append( client)
    for client in drop:
      self.disconnectplayer( client )

  def disconnectplayer(self,client):
  
    if not client in self.clients: return

    print 'disconnectplayer',client
    del self.clients[self.clients.index(client)]

    self.playersOnline -= 1
    
    if self.turn == -1:
      # Renumber players
      for i in range(0,len(self.clients)):
        self.clients[i].player = i
      self.sendplayercount()

  def addplayer(self,client):

    client.player = len(self.clients)
    client.game = self
    self.clients.append( client )

    # Update all clients with new player count (and their teams)
    self.sendplayercount()

    if self.turn == 0:
      self.startgame()    
    

def joinNextGame(client):
  if len(games) == 0:
    games.append( Game() )

  print '1games',len(games),'turn',games[-1].turn

  if games[-1].turn != -1:
    games.append( Game() )

  print '2games',len(games),'turn',games[-1].turn

  games[-1].addplayer( client )

  #return games[0],player # Set these on the player object

#game = Game()
#print game.gamestate


class ServerApplication(WebSocketApplication):
  def on_open(self):
    print "newconnection"
    self.status = 0

  def on_message(self, message):
  
    # join request
    if self.status == 0:
    
      # Find game to join
      self.status = 1
      joinNextGame(self)
      
      # GAME NOW STARTS, SEND gamestate TO ALL PLAYERS (TODO)
      #games[0].startgame()
      #self.ws.send( json.dumps(self.game.gamestate) )
    elif self.game.turn >= 0:
      #print 'got',message
      
      try:
        msg = json.loads(message)
      except:
        self.game.disconnectplayer(self)
        return

      self.game.addorders( self.player, msg )
      
      #self.ws.send( json.dumps(self.game.gamestate) )
    else:
      # drop player here
      self.game.disconnectplayer(self)

  def on_close(self, reason):
    # FIXME: Ensure graceful disconnect of players
    self.game.disconnectplayer(self)
    #print reason
  
WebSocketServer(
  ('', 29349),
  Resource({'/': ServerApplication})
).serve_forever()