# Blockchain-Based Voting System

## Network Layer Implementation

This directory contains the implementation of the network layer for a peer-to-peer blockchain-based voting system. The network layer consists of a tracker server and peer nodes that can communicate with each other.

### Components

1. **Tracker Server (`tracker.py`)**: 
   - Centralized registry that keeps track of all active peers in the network
   - Provides peer discovery services
   - Maintains a list of peers which is updated when a peer joins or leaves
   - Notifies all peers when there are changes to the peer list

2. **Protocol Definitions (`protocol.py`)**:
   - Defines message formats and types for communication between nodes
   - Provides utility functions for sending and receiving messages
   - Handles network errors and connection management

3. **Peer Node (`peer.py`)**:
   - Connects to the tracker server and other peers
   - Maintains a list of peers in the network
   - Handles incoming connections and processes messages
   - Provides methods for broadcasting blocks and votes to the network

### How to Run

#### Starting the Tracker Server

```bash
python tracker.py [--host HOST] [--port PORT]
```

Default values:
- host: 0.0.0.0 (all interfaces)
- port: 8000

#### Starting a Peer Node

```bash
python peer.py [--host HOST] [--port PORT] [--tracker-host TRACKER_HOST] [--tracker-port TRACKER_PORT]
```

Default values:
- host: 0.0.0.0 (all interfaces)
- port: 0 (OS-assigned)
- tracker-host: localhost
- tracker-port: 8000

### Message Types

The protocol defines the following message types:

#### Tracker-related Messages
- `register`: Register a peer with the tracker
- `heartbeat`: Keep the peer registration active
- `get_peers`: Request the list of active peers
- `unregister`: Remove a peer from the tracker
- `peer_list_update`: Notification of peer list changes

#### Blockchain-related Messages (to be implemented)
- `new_block`: Announce a new block
- `get_blocks`: Request blocks from a peer
- `blocks_response`: Response with requested blocks
- `get_chain_info`: Request information about the blockchain
- `chain_info_response`: Response with chain information

#### Application-related Messages (to be implemented)
- `new_vote`: Announce a new vote
- `get_votes`: Request votes from a peer
- `votes_response`: Response with requested votes

### Network Topology

The network follows a hybrid peer-to-peer architecture:
- A central tracker server provides peer discovery
- Peers connect directly to each other for blockchain operations
- Each peer maintains a full copy of the blockchain
- Updates are propagated through the network via broadcasts

### Next Steps

With the network layer in place, the next steps are:
1. Implement the blockchain core components
2. Develop the voting application logic
3. Integrate the components into a complete system
4. Test the system for resilience and functionality

## Project Structure

```
blockchain-voting/
├── src/
│ ├── network/
│ │ ├── tracker.py      # Tracker server implementation
│ │ ├── peer.py         # Peer node implementation
│ │ └── protocol.py     # Network protocol definitions
│ ├── blockchain/       # (To be implemented)
│ │ ├── block.py        # Block structure
│ │ ├── chain.py        # Blockchain operations
│ │ └── mining.py       # Mining algorithm
│ └── application/      # (To be implemented)
│   ├── voting.py       # Voting application logic
│   └── cli.py          # Command-line interface
├── README.md
└── ...
```