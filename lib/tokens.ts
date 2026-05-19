// lib/tokens.ts
export const tokens = {
  ink:        "#1d1b18",
  paper:      "#f7f4ee",
  paperAlt:   "#efeae0",
  line:       "#cdc6b8",
  lineSoft:   "#e3ddd0",
  muted:      "#7d7568",
  accent:     "#7a5c3e",
  accentSoft: "#d8c8ac",
  danger:     "#8a4a3c",
} as const;

export type Token = keyof typeof tokens;
