# HOP AI - RAG System Testing Interface

A modern React TypeScript application for testing RAG (Retrieval-Augmented Generation) systems with a beautiful UI built with Tailwind CSS.

## Features

- **Real-time Chat Interface**: Stream messages to your backend with live response times
- **Document Upload System**: Upload and index documents with configurable categories
- **Prompt Management**: Create, edit, and manage system prompts
- **Configuration Management**: Configure user types, application modes, and backend settings
- **Responsive Design**: Modern UI with smooth animations and transitions
- **TypeScript**: Full type safety throughout the application

## Tech Stack

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Context API** for state management
- **Modern ES6+** features

## Getting Started

### Prerequisites

- Node.js 16+ 
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd hop-ai-react
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The application will be available at `http://localhost:3000`

### Building for Production

```bash
npm run build
```

## Project Structure

```
src/
├── components/          # React components
│   ├── ChatInterface.tsx
│   ├── ChatInput.tsx
│   ├── ChatMessages.tsx
│   ├── DocumentUpload.tsx
│   ├── Dropdown.tsx
│   └── PromptsPage.tsx
├── contexts/           # React contexts
│   └── ConfigContext.tsx
├── services/           # API services
│   └── api.ts
├── types/              # TypeScript type definitions
│   └── index.ts
├── App.tsx            # Main app component
├── index.tsx          # Entry point
└── index.css          # Global styles with Tailwind
```

## Key Components

### ChatInterface
The main chat interface with sidebar configuration and document upload functionality.

### DocumentUpload
Handles file uploads with progress tracking and configurable indexing options.

### PromptsPage
Manages system prompts with CRUD operations and real-time editing.

### Dropdown
Reusable dropdown component with TypeScript support.

## Configuration

The application supports various configuration options:

- **User Types**: Developer, Educator, Regular User
- **Application Modes**: Chatbot, Quiz Generator, PDF Generator, Voiceover
- **Backend Settings**: URL and Provider ID configuration
- **Document Indexing**: Global and Provider-based indexing with category selection

## API Integration

The application expects a backend API with the following endpoints:

- `POST /chat` - Streaming chat endpoint
- `POST /clear-session` - Clear chat session
- `POST /upload-documents` - Document upload endpoint
- `GET /prompts` - Get prompts list
- `GET /prompts/:id` - Get specific prompt
- `POST /prompts` - Create new prompt
- `PUT /prompts/:id` - Update prompt
- `DELETE /prompts/:id` - Delete prompt

## Styling

The application uses Tailwind CSS with custom components and utilities:

- Custom color palette with primary colors
- Responsive design with mobile-first approach
- Smooth animations and transitions
- Consistent spacing and typography

## Development

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

### Code Style

- TypeScript for type safety
- Functional components with hooks
- Consistent naming conventions
- Proper error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue in the repository.
