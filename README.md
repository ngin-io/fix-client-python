# quickfix-client-python

Sample application demonstrating how to connect and interact with BTC Markets' FIX engine using a Python application.

## Prerequisites

The following dependencies are required:

- `openssl` development headers
- `poetry` (recommended for package management)
- `x86 processor` (ARM is currently not supported)

For Ubuntu users:

```bash
sudo apt get install python3-poetry libssl-dev
```

For other operating systems, please refer to their respective documentation for installing these dependencies.

## Installation

```bash
poetry install
poetry shell
```

## Configuration

A template configuration file should be located at `resources/template.cfg`

1. Set connection host: `SocketConnectHost=fix.btcmarkets.net`
2. Set SenderCompID: `SenderCompID=Public API key generated at BTC Markets website`
3. Set PrivateKey: `PrivateKey=Secret API key generated at BTC Markets website`

## Example:

Basic usage:

```bash
cd examples/threaded_workflow
```

Modify the config.cfg file to include the target API endpoints and credentials.

Execute:

```bash
python run.py
```

The `run.py` file contains an illustration implementation following the flow:

1. Application `Logon` to FIX server -> `--------- Logon -FIX.4.4:PUBLIC_API_KEY->BTCM ---------`. Sleep 2 seconds
2. On successful logon, a `limit order` is created -> `--------- Received execution report for limit order, Id: ID-[timestamp], Status: 0`. Sleep 2 seconds
3. On successful order creation, initiates `order status` request -> `--------- Received execution report for order status: 0`. Sleep 2 seconds
4. On successful order status, initiates `order cancel` request -> `--------- Received execution report for cancel order, Id: ID-[timestamp], Status: 4`. Sleep 2 seconds
5. Application waits for Heartbeat (configured in property file) -> `--------- Heartbeat --------- SenderCompID: [public_api_key], SendTime: [timestamp]`
6. After heartbeat received -> Processes incoming heartbeat message
7. On the heartbeat, sends order with invalid parameters to simulate order reject -> `Received order reject. Order: SeqNumber: [7]. Reason: [Value is incorrect (out of range) for this tag, field=103]`
8. On the next heartbeat, sends cancel order with non-existing ID -> `---------  Received order reject. Order: SeqNumber: [10]. Reason: [Required tag missing, field=37] ---------`
9. On the upcoming heartbeat, shuts down initiator. Before logout is initiated -> `---------  Received message: [Logout] ---------`

## Implementation Details

The application implements a `FixClientSampleApplication` class that handles:

- FIX message processing
- Order creation and cancellation
- Order status requests
- Heartbeat monitoring
- Error handling

The sample demonstrates proper connection handling, order lifecycle management, and error scenarios when interacting with the BTC Markets FIX engine.

## Note:

```

```
