import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  CssBaseline,
  Divider,
  Drawer,
  Grid,
  IconButton,
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  ThemeProvider,
  Toolbar,
  Tooltip,
  Typography,
  createTheme,
} from "@mui/material";
import ArrowBack from "@mui/icons-material/ArrowBack";
import BugReport from "@mui/icons-material/BugReport";
import CheckCircle from "@mui/icons-material/CheckCircle";
import ErrorOutline from "@mui/icons-material/ErrorOutline";
import GitHub from "@mui/icons-material/GitHub";
import History from "@mui/icons-material/History";
import Logout from "@mui/icons-material/Logout";
import NotificationsActive from "@mui/icons-material/NotificationsActive";
import OpenInNew from "@mui/icons-material/OpenInNew";
import Rule from "@mui/icons-material/Rule";
import Shield from "@mui/icons-material/Shield";
import Timeline from "@mui/icons-material/Timeline";
import { initialIncidents } from "./data/incidents.js";

const severityColor = {
  Critical: "error",
  High: "warning",
  Medium: "info",
  Low: "success",
};

const statusColor = {
  "Awaiting approval": "warning",
  "Issue opened": "success",
  Resolved: "default",
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1b4d89",
    },
    secondary: {
      main: "#bf3b46",
    },
    background: {
      default: "#f4f7fb",
      paper: "#ffffff",
    },
    text: {
      primary: "#182231",
      secondary: "#596579",
    },
  },
  shape: {
    borderRadius: 8,
  },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontSize: "2.7rem",
      fontWeight: 800,
      letterSpacing: 0,
    },
    h2: {
      fontSize: "1.65rem",
      fontWeight: 800,
      letterSpacing: 0,
    },
    h3: {
      fontSize: "1.2rem",
      fontWeight: 750,
      letterSpacing: 0,
    },
    button: {
      textTransform: "none",
      fontWeight: 700,
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          minHeight: 40,
        },
      },
    },
  },
});

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => sessionStorage.getItem("github_authenticated") === "true",
  );
  const [page, setPage] = useState("alerts");
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [incidents, setIncidents] = useState(initialIncidents);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    if (params.get("auth") === "github" && params.get("login") === "success") {
      sessionStorage.setItem("github_authenticated", "true");
      setIsAuthenticated(true);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.id === selectedIncidentId),
    [incidents, selectedIncidentId],
  );

  const awaitingApproval = incidents.filter(
    (incident) => incident.status === "Awaiting approval",
  );

  const approveIssue = (incidentId) => {
    setIncidents((currentIncidents) =>
      currentIncidents.map((incident) =>
        incident.id === incidentId
          ? {
              ...incident,
              status: "Issue opened",
              gitHubIssue: `GH-${Math.floor(8500 + Math.random() * 300)}`,
            }
          : incident,
      ),
    );
  };

  const openDetail = (incidentId) => {
    setSelectedIncidentId(incidentId);
    setPage("detail");
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      sessionStorage.removeItem("github_authenticated");
      setIsAuthenticated(false);
      window.location.replace("/");
    }
  };

  if (!isAuthenticated) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LoginPage
          onLogin={() => {
            window.location.href = `${API_BASE_URL}/auth/github/login`;
          }}
        />
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="app-shell">
        <Navigation
          activePage={page}
          onNavigate={(nextPage) => {
            setPage(nextPage);
            setSelectedIncidentId(null);
          }}
          onLogout={handleLogout}
          pendingCount={awaitingApproval.length}
        />
        <Box component="main" className="main-content">
          <TopBar pendingCount={awaitingApproval.length} />
          {page === "alerts" && (
            <AlertsPage
              incidents={incidents}
              onApprove={approveIssue}
              onOpenDetail={openDetail}
            />
          )}
          {page === "history" && (
            <HistoryPage incidents={incidents} onOpenDetail={openDetail} />
          )}
          {page === "detail" && selectedIncident && (
            <IncidentDetail
              incident={selectedIncident}
              onApprove={approveIssue}
              onBack={() => setPage("history")}
            />
          )}
          {page === "detail" && !selectedIncident && (
            <EmptyState
              title="Select an error"
              body="Open an incident from alerts or history to inspect the AI triage details."
            />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

function LoginPage({ onLogin }) {
  return (
    <Box className="login-page">
      <Box className="login-panel">
        <Stack spacing={3}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Avatar className="brand-avatar">
              <Shield />
            </Avatar>
            <Box>
              <Typography variant="overline" color="primary">
                Detect
              </Typography>
              <Typography variant="h1">AI Incident Response Engineer</Typography>
            </Box>
          </Stack>
          <Typography variant="body1" color="text.secondary">
            Sign in with GitHub to review AI-detected incidents, approve issue
            creation, and keep a clear history of every error investigation.
          </Typography>
          <Stack className="login-metrics" direction={{ xs: "column", sm: "row" }}>
            <Metric label="AI confidence" value="96%" />
            <Metric label="Pending approvals" value="2" />
            <Metric label="Issues opened" value="18" />
          </Stack>
          <Button
            size="large"
            variant="contained"
            startIcon={<GitHub />}
            onClick={onLogin}
          >
            Continue with GitHub
          </Button>
        </Stack>
      </Box>
      <Box className="login-visual" aria-hidden="true">
        <Paper className="signal-card" elevation={0}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Avatar className="critical-avatar">
              <ErrorOutline />
            </Avatar>
            <Box>
              <Typography variant="h3">Payment API 500 spike</Typography>
              <Typography variant="body2" color="text.secondary">
                Human approval required
              </Typography>
            </Box>
          </Stack>
          <LinearProgress variant="determinate" value={86} color="error" />
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip size="small" color="error" label="Critical" />
            <Chip size="small" label="413 grouped logs" />
            <Chip size="small" label="GitHub draft ready" />
          </Stack>
        </Paper>
      </Box>
    </Box>
  );
}

function Navigation({ activePage, onNavigate, onLogout, pendingCount }) {
  return (
    <Drawer variant="permanent" className="side-nav" PaperProps={{ elevation: 0 }}>
      <Toolbar className="nav-brand">
        <Avatar className="brand-avatar">
          <Shield />
        </Avatar>
        <Box>
          <Typography variant="subtitle1" fontWeight={800}>
            Detect
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Incident Response
          </Typography>
        </Box>
      </Toolbar>
      <Divider />
      <List className="nav-list">
        <ListItemButton
          selected={activePage === "alerts"}
          onClick={() => onNavigate("alerts")}
        >
          <ListItemIcon>
            <NotificationsActive />
          </ListItemIcon>
          <ListItemText primary="Alerts" />
          {pendingCount > 0 && (
            <Chip size="small" color="warning" label={pendingCount} />
          )}
        </ListItemButton>
        <ListItemButton
          selected={activePage === "history"}
          onClick={() => onNavigate("history")}
        >
          <ListItemIcon>
            <History />
          </ListItemIcon>
          <ListItemText primary="History" />
        </ListItemButton>
      </List>
      <Box className="nav-footer">
        <Button
          fullWidth
          variant="outlined"
          color="inherit"
          startIcon={<Logout />}
          onClick={onLogout}
        >
          Sign out
        </Button>
      </Box>
    </Drawer>
  );
}

function TopBar({ pendingCount }) {
  return (
    <AppBar position="sticky" elevation={0} className="top-bar">
      <Toolbar>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h2">Incident command center</Typography>
          <Typography variant="body2" color="text.secondary">
            AI triage with human approval before opening GitHub issues.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1.25} alignItems="center">
          <Chip
            icon={<Rule />}
            color={pendingCount > 0 ? "warning" : "success"}
            label={`${pendingCount} approvals`}
          />
          <Avatar className="user-avatar">GH</Avatar>
        </Stack>
      </Toolbar>
    </AppBar>
  );
}

function AlertsPage({ incidents, onApprove, onOpenDetail }) {
  const awaitingApproval = incidents.filter(
    (incident) => incident.status === "Awaiting approval",
  );
  const openIssues = incidents.filter((incident) => incident.status === "Issue opened");
  const criticalCount = incidents.filter(
    (incident) => incident.severity === "Critical",
  ).length;

  return (
    <Stack spacing={3}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <SummaryCard icon={<NotificationsActive />} label="Awaiting approval" value={awaitingApproval.length} />
        </Grid>
        <Grid item xs={12} md={4}>
          <SummaryCard icon={<GitHub />} label="GitHub issues opened" value={openIssues.length} />
        </Grid>
        <Grid item xs={12} md={4}>
          <SummaryCard icon={<ErrorOutline />} label="Critical signals" value={criticalCount} />
        </Grid>
      </Grid>

      <Stack spacing={2}>
        <SectionHeader
          title="Approval requests"
          subtitle="Review AI analysis before a GitHub issue is opened."
        />
        {awaitingApproval.length === 0 && (
          <EmptyState
            title="No approvals waiting"
            body="Every current incident has already been handled."
          />
        )}
        {awaitingApproval.map((incident) => (
          <IncidentCard
            key={incident.id}
            incident={incident}
            onApprove={onApprove}
            onOpenDetail={onOpenDetail}
            approvalMode
          />
        ))}
      </Stack>

      <Stack spacing={2}>
        <SectionHeader
          title="Active alert stream"
          subtitle="Live-looking frontend data for the detection console."
        />
        {incidents.slice(0, 3).map((incident) => (
          <IncidentCard
            key={incident.id}
            incident={incident}
            onApprove={onApprove}
            onOpenDetail={onOpenDetail}
          />
        ))}
      </Stack>
    </Stack>
  );
}

function HistoryPage({ incidents, onOpenDetail }) {
  return (
    <Stack spacing={2}>
      <SectionHeader
        title="Error history"
        subtitle="Open any error to view details, evidence, impact, and the generated response plan."
      />
      <Paper elevation={0} className="history-list">
        {incidents.map((incident, index) => (
          <Box key={incident.id}>
            <ListItemButton
              className="history-row"
              onClick={() => onOpenDetail(incident.id)}
            >
              <ListItemIcon>
                <BugReport color={severityColor[incident.severity]} />
              </ListItemIcon>
              <ListItemText
                primary={
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1}
                    alignItems={{ xs: "flex-start", sm: "center" }}
                  >
                    <Typography variant="subtitle1" fontWeight={750}>
                      {incident.title}
                    </Typography>
                    <Chip
                      size="small"
                      color={severityColor[incident.severity]}
                      label={incident.severity}
                    />
                    <Chip
                      size="small"
                      color={statusColor[incident.status]}
                      label={incident.status}
                    />
                  </Stack>
                }
                secondary={`${incident.id} • ${incident.service} • ${incident.detectedAt}`}
              />
              <Tooltip title="Open details">
                <OpenInNew color="action" />
              </Tooltip>
            </ListItemButton>
            {index < incidents.length - 1 && <Divider />}
          </Box>
        ))}
      </Paper>
    </Stack>
  );
}

function IncidentDetail({ incident, onApprove, onBack }) {
  return (
    <Stack spacing={2.5}>
      <Button
        className="back-button"
        startIcon={<ArrowBack />}
        onClick={onBack}
        color="inherit"
      >
        Back to history
      </Button>
      <Paper elevation={0} className="detail-header">
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          justifyContent="space-between"
        >
          <Box>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip color={severityColor[incident.severity]} label={incident.severity} />
              <Chip color={statusColor[incident.status]} label={incident.status} />
              <Chip label={incident.environment} />
            </Stack>
            <Typography variant="h2" mt={1.5}>
              {incident.title}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {incident.id} • {incident.service} • Detected {incident.detectedAt}
            </Typography>
          </Box>
          <Stack spacing={1} alignItems={{ xs: "stretch", md: "flex-end" }}>
            <Chip icon={<Timeline />} label={`${incident.confidence}% AI confidence`} />
            {incident.status === "Awaiting approval" ? (
              <Button
                variant="contained"
                color="secondary"
                startIcon={<GitHub />}
                onClick={() => onApprove(incident.id)}
              >
                Approve GitHub issue
              </Button>
            ) : (
              <Chip
                color="success"
                icon={<CheckCircle />}
                label={incident.gitHubIssue || "Completed"}
              />
            )}
          </Stack>
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <DetailPanel title="AI analysis">
            <Typography>{incident.summary}</Typography>
            <Alert severity="info" className="detail-alert">
              {incident.signal}
            </Alert>
            <Typography variant="subtitle2">Impact</Typography>
            <Typography color="text.secondary">{incident.impact}</Typography>
            <Typography variant="subtitle2">Recommendation</Typography>
            <Typography color="text.secondary">{incident.recommendation}</Typography>
          </DetailPanel>
        </Grid>
        <Grid item xs={12} md={5}>
          <DetailPanel title="Response owner">
            <Stack spacing={1.5}>
              <KeyValue label="Owner" value={incident.owner} />
              <KeyValue label="Service" value={incident.service} />
              <KeyValue label="Environment" value={incident.environment} />
              <KeyValue label="GitHub issue" value={incident.gitHubIssue || "Awaiting approval"} />
            </Stack>
          </DetailPanel>
        </Grid>
        <Grid item xs={12} md={6}>
          <DetailPanel title="Timeline">
            <Stack spacing={1.25}>
              {incident.timeline.map((event) => (
                <Stack direction="row" spacing={1.25} key={event}>
                  <CheckCircle color="primary" fontSize="small" />
                  <Typography color="text.secondary">{event}</Typography>
                </Stack>
              ))}
            </Stack>
          </DetailPanel>
        </Grid>
        <Grid item xs={12} md={6}>
          <DetailPanel title="Log evidence">
            <Stack spacing={1}>
              {incident.logs.map((log) => (
                <Box component="code" className="log-line" key={log}>
                  {log}
                </Box>
              ))}
            </Stack>
          </DetailPanel>
        </Grid>
      </Grid>
    </Stack>
  );
}

function IncidentCard({ incident, onApprove, onOpenDetail, approvalMode = false }) {
  return (
    <Paper elevation={0} className="incident-card">
      <Stack
        direction={{ xs: "column", lg: "row" }}
        spacing={2}
        justifyContent="space-between"
      >
        <Stack spacing={1.25} flex={1}>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip
              size="small"
              color={severityColor[incident.severity]}
              label={incident.severity}
            />
            <Chip
              size="small"
              color={statusColor[incident.status]}
              label={incident.status}
            />
            <Chip size="small" label={incident.service} />
          </Stack>
          <Typography variant="h3">{incident.title}</Typography>
          <Typography color="text.secondary">{incident.summary}</Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
            <Typography variant="caption" color="text.secondary">
              {incident.id}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Detected {incident.detectedAt}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {incident.confidence}% confidence
            </Typography>
          </Stack>
        </Stack>
        <Stack
          direction={{ xs: "row", sm: "row", lg: "column" }}
          spacing={1}
          className="card-actions"
        >
          <Button
            variant={approvalMode ? "outlined" : "text"}
            startIcon={<OpenInNew />}
            onClick={() => onOpenDetail(incident.id)}
          >
            Details
          </Button>
          {incident.status === "Awaiting approval" && (
            <Button
              variant="contained"
              color="secondary"
              startIcon={<GitHub />}
              onClick={() => onApprove(incident.id)}
            >
              Approve
            </Button>
          )}
        </Stack>
      </Stack>
    </Paper>
  );
}

function SectionHeader({ title, subtitle }) {
  return (
    <Box>
      <Typography variant="h2">{title}</Typography>
      <Typography color="text.secondary">{subtitle}</Typography>
    </Box>
  );
}

function SummaryCard({ icon, label, value }) {
  return (
    <Paper elevation={0} className="summary-card">
      <Avatar className="summary-icon">{icon}</Avatar>
      <Box>
        <Typography variant="h2">{value}</Typography>
        <Typography color="text.secondary">{label}</Typography>
      </Box>
    </Paper>
  );
}

function DetailPanel({ title, children }) {
  return (
    <Paper elevation={0} className="detail-panel">
      <Typography variant="h3" mb={2}>
        {title}
      </Typography>
      <Stack spacing={1.5}>{children}</Stack>
    </Paper>
  );
}

function EmptyState({ title, body }) {
  return (
    <Paper elevation={0} className="empty-state">
      <Typography variant="h3">{title}</Typography>
      <Typography color="text.secondary">{body}</Typography>
    </Paper>
  );
}

function KeyValue({ label, value }) {
  return (
    <Stack direction="row" justifyContent="space-between" spacing={2}>
      <Typography color="text.secondary">{label}</Typography>
      <Typography fontWeight={750} textAlign="right">
        {value}
      </Typography>
    </Stack>
  );
}

function Metric({ label, value }) {
  return (
    <Box className="metric">
      <Typography variant="h3">{value}</Typography>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

export default App;
