import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: { main: '#2196f3', dark: '#1e88e5', contrastText: '#fff' },
    secondary: { main: '#9c27b0' },
    error: { main: '#f44336' },
    warning: { main: '#ff9800' },
    info: { main: '#0288d1' },
    success: { main: '#4caf50' },
    background: { default: '#fff', paper: '#fff' },
    grey: {
      100: '#f6f6f6',
      200: '#eeeeee',
      300: '#e0e0e0',
      400: '#bdbdbd',
      600: '#757575',
      700: '#616161',
      900: '#212121',
    },
    text: { primary: 'rgba(0,0,0,0.87)', secondary: 'rgba(0,0,0,0.6)' },
  },
  shape: { borderRadius: 4 },
  typography: {
    fontFamily: '"Lato", "Roboto", "Helvetica", "Arial", sans-serif',
    h5: { fontWeight: 700, fontSize: '1.5rem' },
    h6: { fontWeight: 700 },
    button: { textTransform: 'none', fontWeight: 600 },
    body2: { fontSize: '0.875rem' },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 700,
          color: 'rgba(0,0,0,0.87)',
          backgroundColor: '#f6f6f6',
          whiteSpace: 'nowrap',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600 },
      },
    },
  },
});

export default theme;

