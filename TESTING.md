# Blockchain Voting System Testing Guide

This document provides comprehensive step-by-step instructions for testing the blockchain voting system. Follow these instructions to verify the functionality, security, and resilience of the blockchain implementation.

## Prerequisites

- Python 3.6 or higher
- All project files from the repository

## Environment Setup
 **Set up a Python virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Linux/macOS
   source venv/bin/activate
   
   # On Windows
   venv\Scripts\activate
   ```

## Network Setup

Setting up a proper peer-to-peer network is essential for testing the blockchain functionality.

### Tracker Server

1. **Start the tracker server** in one terminal from the project root:
   ```bash
   (venv) ~/blockchain-voting$ python src/network/tracker.py
   ```

   The tracker will start listening on the default port (8000).

### Peer Nodes

2. **Start at least three peer nodes** in separate terminals:

   ```bash
   # First peer
   (venv) ~/blockchain-voting/src/network$ python3 peer.py --tracker-host 192.168.1.100 --port 8001
   
   # Second peer
   (venv) ~/blockchain-voting/src/network$ python3 peer.py --tracker-host 192.168.1.100 --port 8002
   
   # Third peer
   (venv) ~/blockchain-voting/src/network$ python3 peer.py --tracker-host 192.168.1.100 --port 8003
   ```

   **Important**: Replace `192.168.1.100` with your tracker server's actual IP address.

## Basic Functionality Testing

### Starting the Application

1. **Start the CLI application** from the project root:
   ```bash
   (venv) ~/blockchain-voting$ python3 -m src.application.cli
   ```

   You should see the blockchain voting system CLI interface.

### Election Management

2. **Create an election**:
   ```
   create_election Presidential_Election Candidate_A,Candidate_B,Candidate_C
   ```
   
   **Note**: Avoid spaces in candidate names or enclose the entire list in quotes.

3. **Verify election creation**:
   ```
   list_elections
   ```
   
   This should display the election you just created with its ID, title, and candidates.

### Voter Registration

4. **Register multiple voters**:
   ```
   register_voter Alice
   register_voter Bob
   register_voter Charlie
   ```

5. **List registered voters**:
   ```
   list_voters
   ```
   
   This will display all registered voters with their IDs. Note each voter's ID for the next steps.

### Voting Process

6. **Cast votes with different voters**:
   
   First voter (should already be selected):
   ```
   cast_vote Candidate_A
   ```
   
   Select second voter and cast vote:
   ```
   select_voter <Bob's_voter_ID>
   cast_vote Candidate_B
   ```
   
   Select third voter and cast vote:
   ```
   select_voter <Charlie's_voter_ID>
   cast_vote Candidate_C
   ```

7. **View election results**:
   ```
   get_results
   ```
   
   This should show one vote for each candidate.

8. **End the election**:
   ```
   end_election
   ```
   
   This finalizes the election and displays the final results.

9. **View the blockchain**:
   ```
   view_blockchain --full
   ```
   
   Examine the blockchain structure, noting the transactions (votes) in each block.

## Security Testing

The following tests verify the security features of the blockchain.

### Double-Voting Prevention

1. **Attempt to vote twice with the same voter**:
   ```
   cast_vote Candidate_A
   ```
   
   The system should reject this with a message indicating the voter has already cast a vote.

### Blockchain Integrity Verification

2. **Verify blockchain integrity**:
   ```
   verify_blockchain
   ```
   
   This should confirm the blockchain is valid and has not been tampered with.

### Tamper Resistance Demonstration

3. **Tamper with a block**:
   ```
   tamper_block 2 candidate Candidate_Z
   ```
   
   This simulates malicious modification of a block's data.

4. **Verify the blockchain again**:
   ```
   verify_blockchain
   ```
   
   Verification should fail, demonstrating how the blockchain detects tampering.

5. **View the tampered blockchain**:
   ```
   view_blockchain
   ```
   
   Observe how tampering breaks the chain integrity - blocks after the tampered block show invalid previous hash links.

## Advanced Testing

These tests demonstrate more complex features of the blockchain system.

### Vote Simulation

1. **Create a new election**:
   ```
   create_election Senate_Election Senator_X,Senator_Y
   ```

2. **Simulate multiple votes**:
   ```
   simulate_voting 10 50
   ```
   
   This simulates 50 votes from 10 randomly generated voters, demonstrating the system's ability to handle larger voting volumes.

3. **View simulation results**:
   ```
   get_results
   ```

### Fork Handling

4. **Test fork resolution**:
   ```
   simulate_fork
   ```
   
   This demonstrates how the blockchain resolves competing chains using the "longest chain rule".

### Blockchain Persistence

5. **Save the blockchain**:
   ```
   save_blockchain election_backup.json
   ```
   
   This saves the current state of the blockchain to a file.

6. **Load the blockchain**:
   ```
   load_blockchain election_backup.json
   ```
   
   This loads a previously saved blockchain state, demonstrating data persistence.

## P2P Network Testing

With all three components running (tracker server, multiple peer nodes, and CLI), perform these tests to verify network functionality:

### Blockchain Propagation

1. **Create an election and cast votes** using the CLI application

2. **Observe console output** on peer nodes to verify block broadcasting and propagation

### Network Resilience

3. **Test network resilience**:
   - Stop one peer node (Ctrl+C)
   - Create another election and cast a vote
   - Restart the stopped peer node
   - Observe as the node syncs with the network and receives the latest blockchain state

### Fork Resolution in Network

4. **Test fork resolution across the network**:
   - Temporarily disconnect two peer nodes from each other
   - Cast different votes on each isolated node
   - Reconnect the nodes
   - Observe as the network resolves the conflict using the longest chain rule

## Troubleshooting

If you encounter issues during testing, consider the following solutions:

- **Connection issues**: 
  - Ensure you're using the correct IP address for the tracker server
  - Check that firewall settings allow the required ports
  - Verify all components are running in the correct order (tracker first, then peers)

- **Voting failures**:
  - Ensure you've created an election and selected a voter
  - Check that the election is still active (not ended)
  - Verify the candidate name exists and is spelled correctly

- **Blockchain issues**:
  - Run `verify_blockchain` to check for integrity issues
  - Examine the console logs for error messages

- **Format issues**:
  - For candidate names with spaces, enclose them in quotes: `"John Doe,Jane Smith"`
  - Or use underscores instead of spaces: `John_Doe,Jane_Smith`

## Conclusion

Successful completion of these tests demonstrates the core blockchain principles:
- Immutability and tamper resistance
- Distributed consensus
- Security against double-spending (double-voting)
- Resilience through peer-to-peer networking

The blockchain voting system provides a transparent, secure way to conduct elections where the integrity of the votes is protected by the blockchain's inherent properties.