# Dashboard Setup Instructions

## Prerequisites

Before running the dashboard, you need to fix the npm cache permissions issue.

## Fix npm Permissions (Required)

Run the following command to fix npm cache permissions:

```bash
sudo chown -R $(id -u):$(id -g) "$HOME/.npm"
```

Or specifically:
```bash
sudo chown -R 501:20 "/Users/kei/.npm"
```

## Installation Steps

1. **Install Dependencies**:
   ```bash
   cd /Users/kei/Documents/autobot/dashboard
   npm install
   ```

2. **Configure Environment**:
   The `.env` file is already created with default values:
   ```
   VITE_API_URL=http://localhost:8000
   VITE_WS_URL=ws://localhost:8000
   ```

3. **Start Development Server**:
   ```bash
   npm run dev
   ```

   The dashboard will be available at `http://localhost:3000`

4. **Build for Production** (Optional):
   ```bash
   npm run build
   npm run preview
   ```

## Troubleshooting

### Port Already in Use
If port 3000 is already in use, Vite will automatically use the next available port (3001, 3002, etc.)

### API Connection Issues
- Make sure the Back Office Server is running at `http://localhost:8000`
- Check that CORS is properly configured on the backend
- Verify WebSocket connection at `ws://localhost:8000/ws/all`

### Build Errors
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear npm cache: `npm cache clean --force`

## Project Structure

All code has been implemented:
- ✅ Common components (Button, Card, Table, Modal, Badge, LoadingSpinner)
- ✅ Layout components (Header, Sidebar, Layout)
- ✅ API client with all backend endpoints
- ✅ WebSocket hook with auto-reconnect
- ✅ Dashboard page with real-time overview
- ✅ Users management page
- ✅ Trading/Positions page
- ✅ Trade history page with filtering
- ✅ Performance analytics page with charts

## Next Steps

After installation:
1. Start the Back Office Server first
2. Start the Dashboard
3. Open `http://localhost:3000` in your browser
4. You should see the Dashboard page

Happy trading!
