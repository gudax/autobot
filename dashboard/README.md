# Multi-Account Trading Dashboard

A modern, real-time trading dashboard for managing multiple trading accounts simultaneously.

## Features

- **Real-time Updates**: WebSocket integration for live position and session monitoring
- **Multi-User Management**: Create, manage, and control multiple trading accounts
- **Trading Execution**: Execute trading signals across all accounts simultaneously
- **Performance Analytics**: Comprehensive charts and statistics
- **Trade History**: Detailed trade logs with filtering capabilities
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Tech Stack

- **Frontend**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **HTTP Client**: Axios
- **Routing**: React Router v6

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Running Back Office Server (see `../back_office_server`)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and set your API URLs:
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

3. Start the development server:
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
dashboard/
├── src/
│   ├── components/
│   │   ├── common/         # Reusable UI components
│   │   └── layout/         # Layout components
│   ├── hooks/              # Custom React hooks
│   ├── pages/              # Page components
│   ├── services/           # API client
│   ├── types/              # TypeScript type definitions
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # App entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── index.html              # HTML template
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
└── tsconfig.json           # TypeScript configuration
```

## Pages

- **Dashboard** (`/`): Overview statistics and quick actions
- **Users** (`/users`): User and session management
- **Trading** (`/trading`): Execute signals and monitor positions
- **Positions** (`/positions`): View open positions (same as Trading)
- **Trades** (`/trades`): Trade history with filtering
- **Performance** (`/performance`): Analytics and performance metrics

## API Integration

The dashboard connects to the Back Office Server API. Make sure the server is running before starting the dashboard.

- **REST API**: All CRUD operations
- **WebSocket**: Real-time updates for positions, sessions, and dashboard

### WebSocket Channels

- `all`: All updates
- `dashboard`: Dashboard metrics updates
- `sessions`: Session status updates
- `positions`: Position updates
- `trading`: Trading execution updates

## Development

### Code Style

- TypeScript for type safety
- Functional components with hooks
- Tailwind CSS utility classes
- Responsive design with mobile-first approach

### Adding New Pages

1. Create page component in `src/pages/`
2. Export from `src/pages/index.ts`
3. Add route in `src/App.tsx`
4. Add navigation link in `src/components/layout/Sidebar.tsx`

## License

Private - Internal Use Only
