# WolfAssistants Landing Page - Next.js 14

This is the Next.js 14 landing page for WolfAssistants, optimized for SEO with Server-Side Rendering (SSR) and Static Site Generation (SSG).

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the landing page.

### Build for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

## 📁 Project Structure

```
landing/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout with metadata
│   ├── page.tsx           # Home page (SSG)
│   ├── pricing/           # Pricing page
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ui/               # UI components (Button, Card, etc.)
│   ├── HeroSection.tsx   # Hero section (Client Component)
│   ├── Navbar.tsx        # Navigation (Client Component)
│   ├── SocialProofBar.tsx # Stats bar (Server Component)
│   └── ProblemStatement.tsx # Problem section (Server Component)
├── lib/                   # Utilities
│   └── api.ts            # API client
└── public/               # Static assets
```

## 🎯 Features

- ✅ **Server-Side Rendering (SSR)** - Fast initial page loads
- ✅ **Static Site Generation (SSG)** - Pre-rendered pages for maximum performance
- ✅ **SEO Optimized** - Full metadata, structured data, Open Graph tags
- ✅ **TypeScript** - Type-safe development
- ✅ **Tailwind CSS** - Utility-first styling
- ✅ **Responsive Design** - Mobile-first approach

## 🔧 Configuration

### Environment Variables

Create `.env.local` file:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# App Domain (for redirects)
NEXT_PUBLIC_APP_URL=http://localhost:3001
```

### Production Environment

For production, set these in your deployment platform (Vercel):

```bash
NEXT_PUBLIC_API_URL=https://api.wolfassistants.com/api/v1
NEXT_PUBLIC_APP_URL=https://app.wolfassistants.com
```

## 📦 Deployment

### Deploy to Vercel

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel
```

3. Configure domain in Vercel Dashboard

### Manual Deployment

```bash
npm run build
npm start
```

## 🔗 Integration with React App

This landing page is designed to work alongside the React app:

- **Landing Domain:** `wolfassistants.com` → Next.js (this project)
- **App Domain:** `app.wolfassistants.com` → React app (existing frontend)

The Next.js app redirects `/dashboard`, `/login`, `/emails`, etc. to the app domain.

## 📝 Next Steps

1. ✅ Project setup complete
2. ✅ Basic components migrated
3. ⏳ Add more landing page sections (Features, Testimonials, FAQ)
4. ⏳ Create pricing page
5. ⏳ Create legal pages (Terms, Privacy, Returns)
6. ⏳ Add SignupModal component
7. ⏳ Deploy to production

## 🐛 Troubleshooting

### Build Errors
- Ensure all dependencies are installed: `npm install`
- Check TypeScript errors: `npm run build`

### API Connection Issues
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS settings on backend

### Styling Issues
- Ensure Tailwind is configured correctly
- Check `tailwind.config.js` content paths

## 📚 Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
