export type Role = "admin" | "champion" | "builder" | "explorer";

export type DevUser = {
  id: string;
  name: string;
  email: string;
  role: Role;
  department: string;
  initials: string;
  hue: number;
};

/** Seeded pilot users for local development, the demo and the pilot deployment (no Entra yet). Password for all: "playground". */
export const DEV_USERS: DevUser[] = [
  { id: "u1", name: "Satya Bonda", email: "satya@playground.local", role: "admin", department: "AI Platform", initials: "SB", hue: 265 },
  { id: "u2", name: "Priya Raman", email: "priya@playground.local", role: "champion", department: "R&A Training", initials: "PR", hue: 330 },
  { id: "u3", name: "Daniel Okafor", email: "daniel@playground.local", role: "builder", department: "Finance", initials: "DO", hue: 190 },
  { id: "u4", name: "Mei Lin", email: "mei@playground.local", role: "builder", department: "Engineering", initials: "ML", hue: 150 },
  { id: "u5", name: "Carlos Mendes", email: "carlos@playground.local", role: "explorer", department: "Sales", initials: "CM", hue: 30 },
  { id: "u6", name: "Aisha Khan", email: "aisha@playground.local", role: "explorer", department: "HR", initials: "AK", hue: 300 },
  { id: "u7", name: "Tom Becker", email: "tom@playground.local", role: "builder", department: "Operations", initials: "TB", hue: 210 },
  { id: "u8", name: "Hannah Weiss", email: "hannah@playground.local", role: "explorer", department: "Legal", initials: "HW", hue: 350 },
  { id: "u9", name: "Ravi Iyer", email: "ravi@playground.local", role: "champion", department: "Procurement", initials: "RI", hue: 120 },
  { id: "u10", name: "Elena Rossi", email: "elena@playground.local", role: "explorer", department: "Marketing", initials: "ER", hue: 20 },
  { id: "u11", name: "Arbaz Sayed", email: "arbazsayed105@gmail.com", role: "builder", department: "Partners", initials: "AS", hue: 95 },
  { id: "u12", name: "Toral Rathod", email: "Toral.Rathod@eduramp.in", role: "builder", department: "Eduramp", initials: "TR", hue: 250 },
  { id: "u13", name: "Joy Das", email: "Joy.Das@wns.com", role: "builder", department: "WNS", initials: "JD", hue: 175 },
  { id: "u14", name: "Amal Socratles", email: "Amal.Socraties@wns.com", role: "builder", department: "WNS", initials: "AS", hue: 45 },
];

export const DEV_PASSWORD = "playground";

export function findDevUser(email: string): DevUser | undefined {
  return DEV_USERS.find((u) => u.email.toLowerCase() === email.trim().toLowerCase());
}

export const ROLE_LABEL: Record<Role, string> = {
  admin: "Admin",
  champion: "Champion",
  builder: "Builder",
  explorer: "Explorer",
};
