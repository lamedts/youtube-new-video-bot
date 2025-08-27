"""OAuth web server for handling Google OAuth2 callbacks."""

import socket
import threading
import time
import webbrowser
from typing import Optional, Tuple
from flask import Flask, request, redirect, session
from werkzeug.serving import make_server
import secrets
import urllib.parse


class OAuthCallbackServer:
    """Temporary web server to handle OAuth2 callbacks."""
    
    def __init__(self, port_range: Tuple[int, int] = (8080, 8089), timeout: int = 300,
                 callback_domain: Optional[str] = None, use_ssl: bool = False,
                 ssl_cert_path: Optional[str] = None, ssl_key_path: Optional[str] = None):
        """Initialize OAuth callback server.
        
        Args:
            port_range: Range of ports to try (start, end)
            timeout: Timeout in seconds for authentication
            callback_domain: Domain for callback URL (None = localhost)
            use_ssl: Whether to use SSL/HTTPS
            ssl_cert_path: Path to SSL certificate file
            ssl_key_path: Path to SSL private key file
        """
        self.port_range = port_range
        self.timeout = timeout
        self.callback_domain = callback_domain
        self.use_ssl = use_ssl
        self.ssl_cert_path = ssl_cert_path
        self.ssl_key_path = ssl_key_path
        
        self.app = None
        self.server = None
        self.port = None
        self.authorization_code = None
        self.state = None
        self.error = None
        self.success = False
        self._server_thread = None
        
    def _find_available_port(self) -> Optional[int]:
        """Find an available port in the specified range."""
        # Use 0.0.0.0 for external domain access, localhost for local
        bind_host = '0.0.0.0' if self.callback_domain else 'localhost'
        
        for port in range(self.port_range[0], self.port_range[1] + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((bind_host, port))
                    return port
            except OSError:
                continue
        return None
    
    def _create_flask_app(self) -> Flask:
        """Create Flask application with OAuth callback endpoint."""
        app = Flask(__name__)
        app.secret_key = secrets.token_urlsafe(32)
        
        @app.route('/oauth2callback')
        def oauth2callback():
            """Handle OAuth2 callback from Google."""
            try:
                # Check for errors in the callback
                error = request.args.get('error')
                if error:
                    self.error = f"OAuth error: {error}"
                    return self._create_error_page(self.error)
                
                # Validate state parameter for security
                returned_state = request.args.get('state')
                if not returned_state or returned_state != self.state:
                    self.error = "Invalid state parameter - possible CSRF attack"
                    return self._create_error_page(self.error)
                
                # Extract authorization code
                code = request.args.get('code')
                if not code:
                    self.error = "No authorization code received"
                    return self._create_error_page(self.error)
                
                # Success - store the authorization code
                self.authorization_code = code
                self.success = True
                
                # Shutdown server after a brief delay
                threading.Timer(1.0, self._shutdown_server).start()
                
                return self._create_success_page()
                
            except Exception as e:
                self.error = f"Callback error: {e}"
                return self._create_error_page(self.error)
        
        @app.route('/health')
        def health():
            """Health check endpoint."""
            return {'status': 'ok', 'port': self.port}
        
        return app
    
    def _create_success_page(self) -> str:
        """Create success page HTML."""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>YouTube Bot - Authorization Successful</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                .container { background: white; padding: 40px; border-radius: 10px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .success { color: #28a745; font-size: 24px; margin-bottom: 20px; }
                .message { color: #666; margin-bottom: 30px; }
                .note { color: #666; font-size: 14px; font-style: italic; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅ Authorization Successful!</div>
                <div class="message">
                    Your YouTube bot has been successfully authorized to access your YouTube data.
                    The authentication process is complete.
                </div>
                <div class="note">
                    You can close this browser tab now. The bot will continue running automatically.
                </div>
            </div>
            <script>
                // Auto-close tab after 3 seconds
                setTimeout(function() {
                    window.close();
                }, 3000);
            </script>
        </body>
        </html>
        '''
    
    def _create_error_page(self, error_message: str) -> str:
        """Create error page HTML."""
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>YouTube Bot - Authorization Failed</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }}
                .container {{ background: white; padding: 40px; border-radius: 10px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .error {{ color: #dc3545; font-size: 24px; margin-bottom: 20px; }}
                .message {{ color: #666; margin-bottom: 20px; }}
                .details {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">❌ Authorization Failed</div>
                <div class="message">
                    There was an error during the OAuth authorization process.
                    Please try again or check the bot logs for more details.
                </div>
                <div class="details">{error_message}</div>
            </div>
        </body>
        </html>
        '''
    
    def _shutdown_server(self):
        """Shutdown the Flask server."""
        if self.server:
            try:
                self.server.shutdown()
            except Exception as e:
                print(f"[oauth] Error shutting down server: {e}")
    
    def start_server(self, state: str) -> Optional[str]:
        """Start the OAuth callback server.
        
        Args:
            state: OAuth state parameter for security validation
            
        Returns:
            URL for OAuth callback or None if server couldn't start
        """
        self.state = state
        self.port = self._find_available_port()
        
        if not self.port:
            print(f"[oauth] No available ports in range {self.port_range}")
            return None
        
        try:
            self.app = self._create_flask_app()
            
            # Determine bind host and callback URL
            if self.callback_domain:
                bind_host = '0.0.0.0'  # Accept external connections
                scheme = 'https' if self.use_ssl else 'http'
                callback_url = f"{scheme}://{self.callback_domain}:{self.port}/oauth2callback"
            else:
                bind_host = 'localhost'
                callback_url = f"http://localhost:{self.port}/oauth2callback"
            
            # Create server with SSL context if needed
            if self.use_ssl and self.ssl_cert_path and self.ssl_key_path:
                import ssl
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(self.ssl_cert_path, self.ssl_key_path)
                print(f"[oauth] Using SSL certificate: {self.ssl_cert_path}")
                
                self.server = make_server(bind_host, self.port, self.app, 
                                        threaded=True, ssl_context=ssl_context)
            else:
                self.server = make_server(bind_host, self.port, self.app, threaded=True)
            
            # Start server in background thread
            self._server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._server_thread.start()
            
            if self.callback_domain:
                print(f"[oauth] OAuth callback server started on {bind_host}:{self.port}")
                print(f"[oauth] External callback URL: {callback_url}")
            else:
                print(f"[oauth] OAuth callback server started on {callback_url}")
            
            return callback_url
            
        except Exception as e:
            print(f"[oauth] Failed to start OAuth server: {e}")
            return None
    
    def wait_for_callback(self) -> Optional[str]:
        """Wait for OAuth callback and return authorization code.
        
        Returns:
            Authorization code or None if failed/timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            if self.success and self.authorization_code:
                print("[oauth] Successfully received authorization code")
                return self.authorization_code
            elif self.error:
                print(f"[oauth] OAuth callback error: {self.error}")
                return None
            
            time.sleep(0.5)  # Check every 500ms
        
        print(f"[oauth] Timeout waiting for OAuth callback after {self.timeout} seconds")
        return None
    
    def stop_server(self):
        """Stop the OAuth callback server."""
        if self.server:
            try:
                self.server.shutdown()
                if self._server_thread and self._server_thread.is_alive():
                    self._server_thread.join(timeout=2.0)
                print("[oauth] OAuth server stopped")
            except Exception as e:
                print(f"[oauth] Error stopping OAuth server: {e}")
    
    def open_authorization_url(self, auth_url: str, auto_browser: bool = True) -> bool:
        """Open authorization URL in browser.
        
        Args:
            auth_url: The OAuth authorization URL
            auto_browser: Whether to automatically open browser
            
        Returns:
            True if browser opened successfully, False otherwise
        """
        if not auto_browser:
            print(f"[oauth] Please visit this URL to authorize the application:")
            print(f"[oauth] {auth_url}")
            return False
        
        try:
            print("[oauth] Opening authorization URL in your default browser...")
            webbrowser.open(auth_url, new=2)  # new=2 opens in new tab
            return True
        except Exception as e:
            print(f"[oauth] Failed to open browser automatically: {e}")
            print(f"[oauth] Please visit this URL manually: {auth_url}")
            return False


def run_oauth_flow(client_secrets_file: str, scopes: list, 
                   port_range: Tuple[int, int] = (8080, 8089),
                   timeout: int = 300, auto_browser: bool = True,
                   callback_domain: Optional[str] = None, use_ssl: bool = False,
                   ssl_cert_path: Optional[str] = None, ssl_key_path: Optional[str] = None) -> Optional[dict]:
    """Run complete OAuth2 flow with temporary web server.
    
    Args:
        client_secrets_file: Path to Google client secrets file
        scopes: List of OAuth scopes to request
        port_range: Range of ports to try for callback server
        timeout: Timeout in seconds for user to complete authorization
        auto_browser: Whether to automatically open browser
        callback_domain: Domain for callback URL (None = localhost)
        use_ssl: Whether to use SSL/HTTPS
        ssl_cert_path: Path to SSL certificate file
        ssl_key_path: Path to SSL private key file
        
    Returns:
        OAuth credentials dict or None if failed
    """
    from google_auth_oauthlib.flow import Flow
    
    server = OAuthCallbackServer(
        port_range, timeout, callback_domain, use_ssl, ssl_cert_path, ssl_key_path
    )
    
    try:
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        
        # Start callback server
        callback_url = server.start_server(state)
        if not callback_url:
            return None
        
        # Create OAuth flow
        flow = Flow.from_client_secrets_file(client_secrets_file, scopes=scopes)
        flow.redirect_uri = callback_url
        
        # Generate authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )
        
        # Open browser
        browser_opened = server.open_authorization_url(authorization_url, auto_browser)
        
        if not auto_browser or not browser_opened:
            print(f"[oauth] Waiting up to {timeout} seconds for authorization...")
        
        # Wait for callback
        authorization_code = server.wait_for_callback()
        
        if not authorization_code:
            return None
        
        # Exchange authorization code for tokens
        print("[oauth] Exchanging authorization code for access tokens...")
        flow.fetch_token(code=authorization_code)
        
        credentials = flow.credentials
        print(f"[oauth] OAuth flow completed successfully, expires at: {credentials.expiry}")
        
        return {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'universe_domain': getattr(credentials, 'universe_domain', 'googleapis.com'),
            'account': getattr(credentials, 'account', ''),
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
    except Exception as e:
        print(f"[oauth] OAuth flow failed: {e}")
        return None
        
    finally:
        server.stop_server()