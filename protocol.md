# GAME STATE

[
  // (0,0)
  {
    "type": "village",
    "owner": 0,
    "size": 159
    "economy": 0,
    "defense": 0,
    "mode": "troops",
    "burning": 0,
    "attacks": [ 0, 0, 0, 0, 0, 0 ],
    "orders":  [ 0, 0, 0, 0, 0, 0 ]
  },
  // (1,0)
  {
    "type": "troll",
    "size": 159
    "economy": 0,
    "burning": 0
    "attacks": [ 0, 0, 0, 0, 0, 0 ]
  }
  // (2,0)
]

# TURN ACTIONS (generated out of "mode" + "orders" above, each TURN)

[
  // "X,Y": [ MODE, N, NE, SE, S, SW, NW ]
  "turn": 0,
  "0,0": [ "", [ 1, 0, 0, 0, 0, 0] ],
  "1,0": [ "", [ 0, 0, 0, 0, 2, 2] ]
]
