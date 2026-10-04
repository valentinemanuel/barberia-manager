# Barbershop Manager

A complete management system for barbershops with an installable PWA, offline support, and automatic synchronization.

## Features

- **Barber management**: Haircut tracking, profit percentages, history
- **Service catalog**: Haircuts, beard trims, dyes with configurable prices
- **Products & consumables**: Stock control, quick sales
- **Cash register closing**: Daily summary, differences, withdrawals
- **Reports**: Earnings by period, haircuts per barber, top-selling products
- **PWA**: Installable on mobile, works offline, automatic sync

## Screenshots

![Admin Dashboard](docs/screenshots/dashboard-admin.png)
![Haircut Registration](docs/screenshots/registro-cortes.png)
![Barber Dashboard](docs/screenshots/dashboard-barbero.png)
![Reports](docs/screenshots/reportes.png)

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm or pnpm

## Installation

### 1. Clone the repository
```bash
git clone <repo-url>
cd barbershop-manager
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend
```bash
cd frontend
npm install
```

## Initial Setup

### Create admin user
```bash
cd backend
python -m app.scripts.create_admin
```

### Environment variables (backend/.env)
```env
DATABASE_URL=sqlite:///./barberia.db
SECRET_KEY=your-very-secure-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

## Usage

### Development
```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Production
```bash
# Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run build
npm run preview
```

## Roles & Permissions

### Admin
- View earnings (daily, weekly, monthly)
- Manage barbers and percentages
- Configure services and prices
- Manage products and stock
- Register expenses
- Perform cash register closing
- View reports and export data

### Barber
- Register their own haircuts
- View their accumulated earnings (their share)
- View their assigned percentage
- Does NOT see other barbers' information
- Does NOT see global earnings

## Available Scripts

### Backend
| Script | Description |
|--------|-------------|
| `uvicorn app.main:app --reload` | Development server |
| `pytest tests/ -v` | Run tests |
| `python -m app.scripts.create_admin` | Create initial admin |

### Frontend
| Script | Description |
|--------|-------------|
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm run preview` | Production preview |

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## License

MIT License - See [LICENSE](LICENSE) for details.
