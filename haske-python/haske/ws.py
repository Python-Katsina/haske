# haske-python/haske/ws.py
"""
WebSocket utilities for Haske framework with Rust acceleration.

This module provides WebSocket support with Rust-accelerated frame parsing,
validation, and broadcasting, integrated with Starlette's WebSocket implementation.
"""

import asyncio
import json
import uuid
import base64
import hashlib
from typing import Dict, List, Optional, Callable, Any, Set, Union
from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketState
from starlette.routing import WebSocketRoute

# Import Rust WebSocket functions
try:
    from _haske_core import (
        WebSocketFrame,
        WebSocketManager,
        WebSocketReceiver,
        websocket_accept_key,
        validate_websocket_frame,
        get_frame_type
    )
    HAS_RUST_WS = True
except ImportError:
    HAS_RUST_WS = False
    
    # Fallback implementations when Rust extension is not available
    class WebSocketFrame:
        def __init__(self, opcode: int, payload: bytes, is_final: bool = True, is_masked: bool = False):
            self.opcode = opcode
            self.payload = payload
            self.is_final = is_final
            self.is_masked = is_masked
        
        @staticmethod
        def parse(data: bytes):
            # Simple fallback implementation - only handles basic text frames
            if len(data) < 2:
                raise ValueError("Frame too short")
            return WebSocketFrame(1, data[2:], True, False)
        
        def to_bytes(self) -> bytes:
            # Simple frame construction
            header = bytes([0x80 | self.opcode, len(self.payload)])
            return header + self.payload
        
        @staticmethod
        def text(text: str) -> 'WebSocketFrame':
            return WebSocketFrame(1, text.encode('utf-8'), True, False)
        
        @staticmethod
        def binary(data: bytes) -> 'WebSocketFrame':
            return WebSocketFrame(2, data, True, False)
        
        @staticmethod
        def close(code: Optional[int] = None, reason: Optional[str] = None) -> 'WebSocketFrame':
            payload = b''
            if code is not None:
                payload += code.to_bytes(2, 'big')
            if reason is not None:
                payload += reason.encode('utf-8')
            return WebSocketFrame(8, payload, True, False)
        
        @staticmethod
        def ping(data: Optional[bytes] = None) -> 'WebSocketFrame':
            return WebSocketFrame(9, data or b'', True, False)
        
        @staticmethod
        def pong(data: Optional[bytes] = None) -> 'WebSocketFrame':
            return WebSocketFrame(10, data or b'', True, False)
    
    class WebSocketManager:
        def __init__(self):
            self.channels: Dict[str, Set[Callable]] = {}
        
        def create_channel(self, channel_id: str, capacity: int = 1000) -> None:
            self.channels[channel_id] = set()
        
        def broadcast(self, channel_id: str, message: bytes) -> int:
            if channel_id not in self.channels:
                raise ValueError("Channel not found")
            # Fallback implementation doesn't actually broadcast
            return len(self.channels[channel_id])
        
        def get_receiver(self, channel_id: str) -> 'WebSocketReceiver':
            if channel_id not in self.channels:
                raise ValueError("Channel not found")
            return WebSocketReceiver()
        
        def remove_channel(self, channel_id: str) -> None:
            self.channels.pop(channel_id, None)
        
        def list_channels(self) -> List[str]:
            return list(self.channels.keys())
    
    class WebSocketReceiver:
        def recv(self) -> Optional[bytes]:
            return None
        
        def recv_blocking(self) -> bytes:
            return b''

class WebSocket:
    """
    Enhanced WebSocket wrapper with Rust acceleration.
    
    Provides high-performance WebSocket operations with Starlette integration.
    """
    
    def __init__(self, websocket: StarletteWebSocket):
        """
        Initialize WebSocket wrapper.
        
        Args:
            websocket: Starlette WebSocket instance
        """
        self._ws = websocket
        self.connection_id = str(uuid.uuid4())
        self._rust_manager = WebSocketManager() if HAS_RUST_WS else None
        
    async def accept(self, subprotocol: str = None) -> None:
        """
        Accept WebSocket connection.
        
        Args:
            subprotocol: Optional subprotocol
        """
        await self._ws.accept(subprotocol=subprotocol)
    
    async def close(self, code: int = 1000, reason: str = None) -> None:
        """
        Close WebSocket connection.
        
        Args:
            code: Close code
            reason: Close reason
        """
        await self._ws.close(code=code, reason=reason)
    
    async def receive_bytes(self) -> bytes:
        """
        Receive raw bytes from WebSocket.
        
        Returns:
            bytes: Received data
            
        Note: Uses Rust validation if available
        """
        data = await self._ws.receive_bytes()
        if HAS_RUST_WS and not validate_websocket_frame(data):
            raise ValueError("Invalid WebSocket frame")
        return data
    
    async def receive_text(self) -> str:
        """
        Receive text from WebSocket.
        
        Returns:
            str: Received text
        """
        return await self._ws.receive_text()
    
    async def receive_json(self) -> Any:
        """
        Receive JSON from WebSocket.
        
        Returns:
            Any: Parsed JSON data
        """
        text = await self.receive_text()
        return json.loads(text)
    
    async def send_bytes(self, data: bytes) -> None:
        """
        Send raw bytes through WebSocket.
        
        Args:
            data: Bytes to send
        """
        await self._ws.send_bytes(data)
    
    async def send_text(self, text: str) -> None:
        """
        Send text through WebSocket.
        
        Args:
            text: Text to send
        """
        await self._ws.send_text(text)
    
    async def send_json(self, data: Any) -> None:
        """
        Send JSON through WebSocket.
        
        Args:
            data: JSON-serializable data
        """
        text = json.dumps(data, default=str)
        await self.send_text(text)
    
    # Rust-accelerated methods
    async def receive_frame(self) -> Optional[WebSocketFrame]:
        """
        Receive and parse WebSocket frame using Rust.
        
        Returns:
            Optional[WebSocketFrame]: Parsed frame or None
            
        Note: Only available with Rust extension
        """
        if not HAS_RUST_WS:
            raise RuntimeError("Rust WebSocket extension not available")
        
        data = await self.receive_bytes()
        try:
            return WebSocketFrame.parse(data)
        except Exception as e:
            raise ValueError(f"Failed to parse WebSocket frame: {e}")
    
    async def send_frame(self, frame: WebSocketFrame) -> None:
        """
        Send WebSocket frame using Rust.
        
        Args:
            frame: WebSocketFrame to send
            
        Note: Only available with Rust extension
        """
        if not HAS_RUST_WS:
            raise RuntimeError("Rust WebSocket extension not available")
        
        data = frame.to_bytes()
        await self.send_bytes(data)
    
    # High-level messaging
    async def ping(self, data: bytes = None) -> None:
        """Send ping frame."""
        if HAS_RUST_WS:
            frame = WebSocketFrame.ping(data)
            await self.send_frame(frame)
        else:
            await self._ws.send({"type": "websocket.ping", "bytes": data or b''})
    
    async def pong(self, data: bytes = None) -> None:
        """Send pong frame."""
        if HAS_RUST_WS:
            frame = WebSocketFrame.pong(data)
            await self.send_frame(frame)
        else:
            await self._ws.send({"type": "websocket.pong", "bytes": data or b''})
    
    # Connection state
    @property
    def client(self) -> tuple:
        """Get client address."""
        return self._ws.client
    
    @property
    def state(self) -> WebSocketState:
        """Get connection state."""
        return self._ws.state
    
    @property
    def application_state(self) -> Any:
        """Get application state."""
        return self._ws.application_state
    
    def __getattr__(self, name):
        """Delegate unknown attributes to underlying WebSocket."""
        return getattr(self._ws, name)

class WebSocketBroadcaster:
    """
    WebSocket broadcasting manager with Rust acceleration.
    
    Provides efficient message broadcasting to multiple WebSocket connections.
    """
    
    def __init__(self):
        """Initialize WebSocket broadcaster."""
        self._connections: Set[WebSocket] = set()
        self._rust_manager = WebSocketManager() if HAS_RUST_WS else None
        self._channels: Dict[str, Set[WebSocket]] = {}
    
    async def add_connection(self, websocket: WebSocket) -> None:
        """
        Add WebSocket connection to broadcaster.
        
        Args:
            websocket: WebSocket connection
        """
        self._connections.add(websocket)
    
    async def remove_connection(self, websocket: WebSocket) -> None:
        """
        Remove WebSocket connection from broadcaster.
        
        Args:
            websocket: WebSocket connection
        """
        self._connections.discard(websocket)
        # Remove from all channels
        for channel_connections in self._channels.values():
            channel_connections.discard(websocket)
    
    async def broadcast(self, message: Any, channel: str = None) -> int:
        """
        Broadcast message to all connections or specific channel.
        
        Args:
            message: Message to broadcast (can be str, bytes, or dict)
            channel: Optional channel name
            
        Returns:
            int: Number of connections that received the message
        """
        if isinstance(message, dict):
            message = json.dumps(message)
        
        if channel and self._rust_manager and HAS_RUST_WS:
            # Use Rust-accelerated broadcasting
            if isinstance(message, str):
                message = message.encode('utf-8')
            try:
                return self._rust_manager.broadcast(channel, message)
            except Exception:
                # Fall back to Python broadcasting if Rust fails
                pass
        
        # Fallback to Python broadcasting
        connections = self._channels.get(channel, set()) if channel else self._connections
        sent_count = 0
        
        for ws in list(connections):  # Copy to avoid modification during iteration
            try:
                if isinstance(message, str):
                    await ws.send_text(message)
                else:
                    await ws.send_bytes(message)
                sent_count += 1
            except Exception:
                await self.remove_connection(ws)
        
        return sent_count
    
    async def create_channel(self, channel_name: str) -> None:
        """
        Create a new broadcast channel.
        
        Args:
            channel_name: Channel name
        """
        if self._rust_manager and HAS_RUST_WS:
            try:
                self._rust_manager.create_channel(channel_name, 1000)
            except Exception:
                pass  # Fall back to Python implementation
        self._channels[channel_name] = set()
    
    async def add_to_channel(self, websocket: WebSocket, channel_name: str) -> None:
        """
        Add WebSocket to broadcast channel.
        
        Args:
            websocket: WebSocket connection
            channel_name: Channel name
        """
        if channel_name in self._channels:
            self._channels[channel_name].add(websocket)
    
    async def remove_from_channel(self, websocket: WebSocket, channel_name: str) -> None:
        """
        Remove WebSocket from broadcast channel.
        
        Args:
            websocket: WebSocket connection
            channel_name: Channel name
        """
        if channel_name in self._channels:
            self._channels[channel_name].discard(websocket)
    
    def get_channel_connections(self, channel_name: str) -> Set[WebSocket]:
        """
        Get all connections in a channel.
        
        Args:
            channel_name: Channel name
            
        Returns:
            Set[WebSocket]: Set of WebSocket connections
        """
        return self._channels.get(channel_name, set())
    
    def get_all_connections(self) -> Set[WebSocket]:
        """
        Get all connections.
        
        Returns:
            Set[WebSocket]: Set of all WebSocket connections
        """
        return self._connections.copy()

# Global broadcaster instance
_broadcaster = WebSocketBroadcaster()

def get_broadcaster() -> WebSocketBroadcaster:
    """
    Get global WebSocket broadcaster instance.
    
    Returns:
        WebSocketBroadcaster: Global broadcaster instance
    """
    return _broadcaster

# WebSocket route decorator
def websocket_route(path: str, name: str = None):
    """
    Decorator for WebSocket routes.
    
    Args:
        path: WebSocket path
        name: Optional route name
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> WebSocketRoute:
        async def websocket_endpoint(websocket: StarletteWebSocket):
            ws = WebSocket(websocket)
            await _broadcaster.add_connection(ws)
            try:
                await func(ws)
            finally:
                await _broadcaster.remove_connection(ws)
        
        return WebSocketRoute(path, websocket_endpoint, name=name)
    
    return decorator

# Utility functions
def websocket_handshake(key: str) -> str:
    """
    Generate WebSocket accept key for handshake.
    
    Args:
        key: Sec-WebSocket-Key from client
        
    Returns:
        str: Sec-WebSocket-Accept value
    """
    if HAS_RUST_WS:
        return websocket_accept_key(key)
    else:
        # Fallback Python implementation
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        combined = key + GUID
        sha1_hash = hashlib.sha1(combined.encode()).digest()
        return base64.b64encode(sha1_hash).decode()

def is_websocket_upgrade(headers: Dict[str, str]) -> bool:
    """
    Check if request is a WebSocket upgrade.
    
    Args:
        headers: Request headers
        
    Returns:
        bool: True if WebSocket upgrade request
    """
    connection = headers.get('connection', '').lower()
    upgrade = headers.get('upgrade', '').lower()
    return 'upgrade' in connection and upgrade == 'websocket'

def validate_websocket_request(headers: Dict[str, str]) -> bool:
    """
    Validate WebSocket upgrade request.
    
    Args:
        headers: Request headers
        
    Returns:
        bool: True if valid WebSocket upgrade request
    """
    if not is_websocket_upgrade(headers):
        return False
    
    # Check for required headers
    required_headers = ['sec-websocket-key', 'sec-websocket-version']
    return all(header in headers for header in required_headers)

# Example usage classes
class WebSocketHandler:
    """Base class for WebSocket handlers."""
    
    async def on_connect(self, websocket: WebSocket) -> None:
        """Handle WebSocket connection."""
        pass
    
    async def on_message(self, websocket: WebSocket, message: Any) -> None:
        """Handle incoming message."""
        pass
    
    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        pass
    
    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Main WebSocket handling loop."""
        await self.on_connect(websocket)
        
        try:
            while websocket.state == WebSocketState.CONNECTED:
                try:
                    # Try to receive JSON first
                    try:
                        message = await websocket.receive_json()
                    except (json.JSONDecodeError, ValueError):
                        # Fall back to text if not JSON
                        message = await websocket.receive_text()
                    
                    await self.on_message(websocket, message)
                except Exception as e:
                    # Handle specific WebSocket errors
                    if isinstance(e, RuntimeError) and "WebSocket is not connected" in str(e):
                        break
                    # Log other errors but continue
                    print(f"WebSocket error: {e}")
        finally:
            await self.on_disconnect(websocket, 1000)

class LiveSessionManager:
    """Manager for live WebSocket sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, WebSocket] = {}
        self.broadcaster = get_broadcaster()
    
    async def add_session(self, session_id: str, websocket: WebSocket) -> None:
        """
        Add WebSocket session.
        
        Args:
            session_id: Session ID
            websocket: WebSocket connection
        """
        self.sessions[session_id] = websocket
        await self.broadcaster.add_connection(websocket)
    
    async def remove_session(self, session_id: str) -> None:
        """
        Remove WebSocket session.
        
        Args:
            session_id: Session ID
        """
        if session_id in self.sessions:
            ws = self.sessions.pop(session_id)
            await self.broadcaster.remove_connection(ws)
    
    async def broadcast_to_session(self, session_id: str, message: Any) -> bool:
        """
        Send message to specific session.
        
        Args:
            session_id: Session ID
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        if session_id in self.sessions:
            try:
                if isinstance(message, str):
                    await self.sessions[session_id].send_text(message)
                else:
                    await self.sessions[session_id].send_json(message)
                return True
            except Exception:
                await self.remove_session(session_id)
        return False
    
    async def broadcast_to_all(self, message: Any) -> int:
        """
        Broadcast message to all sessions.
        
        Args:
            message: Message to broadcast
            
        Returns:
            int: Number of sessions that received the message
        """
        return await self.broadcaster.broadcast(message)
    
    def get_session_count(self) -> int:
        """
        Get number of active sessions.
        
        Returns:
            int: Number of active sessions
        """
        return len(self.sessions)
    
    def get_session_ids(self) -> List[str]:
        """
        Get all session IDs.
        
        Returns:
            List[str]: List of session IDs
        """
        return list(self.sessions.keys())

# WebSocket connection pool for efficient management
class WebSocketConnectionPool:
    """Pool for managing WebSocket connections efficiently."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.groups: Dict[str, Set[str]] = {}
    
    async def add_connection(self, connection_id: str, websocket: WebSocket) -> None:
        """
        Add connection to pool.
        
        Args:
            connection_id: Unique connection ID
            websocket: WebSocket connection
        """
        self.connections[connection_id] = websocket
    
    async def remove_connection(self, connection_id: str) -> None:
        """
        Remove connection from pool.
        
        Args:
            connection_id: Connection ID to remove
        """
        self.connections.pop(connection_id, None)
        # Remove from all groups
        for group_name, group_connections in self.groups.items():
            group_connections.discard(connection_id)
    
    async def add_to_group(self, connection_id: str, group_name: str) -> None:
        """
        Add connection to group.
        
        Args:
            connection_id: Connection ID
            group_name: Group name
        """
        if group_name not in self.groups:
            self.groups[group_name] = set()
        self.groups[group_name].add(connection_id)
    
    async def remove_from_group(self, connection_id: str, group_name: str) -> None:
        """
        Remove connection from group.
        
        Args:
            connection_id: Connection ID
            group_name: Group name
        """
        if group_name in self.groups:
            self.groups[group_name].discard(connection_id)
    
    async def broadcast_to_group(self, group_name: str, message: Any) -> int:
        """
        Broadcast message to group.
        
        Args:
            group_name: Group name
            message: Message to broadcast
            
        Returns:
            int: Number of connections that received the message
        """
        if group_name not in self.groups:
            return 0
        
        sent_count = 0
        for connection_id in list(self.groups[group_name]):
            if connection_id in self.connections:
                try:
                    ws = self.connections[connection_id]
                    if isinstance(message, str):
                        await ws.send_text(message)
                    else:
                        await ws.send_json(message)
                    sent_count += 1
                except Exception:
                    await self.remove_connection(connection_id)
        
        return sent_count
    
    def get_group_size(self, group_name: str) -> int:
        """
        Get number of connections in group.
        
        Args:
            group_name: Group name
            
        Returns:
            int: Number of connections in group
        """
        return len(self.groups.get(group_name, set()))
    
    def get_total_connections(self) -> int:
        """
        Get total number of connections.
        
        Returns:
            int: Total number of connections
        """
        return len(self.connections)

# Export public API
__all__ = [
    'WebSocket',
    'WebSocketBroadcaster',
    'WebSocketHandler',
    'LiveSessionManager',
    'WebSocketConnectionPool',
    'websocket_route',
    'get_broadcaster',
    'websocket_handshake',
    'is_websocket_upgrade',
    'validate_websocket_request',
    'HAS_RUST_WS'
]

# Global connection pool instance
_connection_pool = WebSocketConnectionPool()

def get_connection_pool() -> WebSocketConnectionPool:
    """
    Get global WebSocket connection pool instance.
    
    Returns:
        WebSocketConnectionPool: Global connection pool instance
    """
    return _connection_pool