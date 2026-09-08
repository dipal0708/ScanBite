// Design tokens for LabelWise — grounded in real Nutrition Facts panels
// (bold rules, condensed numerals) crossed with a friendly game-guide feel.
// See the interactive prototype for these applied to real screens.

export const colors = {
  paper: "#F6F5EF", // background — warm, not the generic AI cream
  ink: "#17231C", // near-black deep green, body text & rules
  brand: "#2F6B4F", // primary green — CTAs, "good" state
  brandDark: "#1F4A36",
  danger: "#B3432B", // rust red — diet-fit / allergen flags
  warning: "#C98A2C", // mustard — moderate flags
  good: "#6FA85C", // leaf green — "fits your profile" badge
  cardBorder: "#D9D4C4",
  surface: "#FFFFFF",
  muted: "#6B7268",
};

export const typography = {
  display: "BarlowCondensed_700Bold", // headline / label-style numerals
  body: "Inter_400Regular",
  bodyMedium: "Inter_600SemiBold",
};

export const spacing = (n: number) => n * 4;

export const radii = {
  sm: 4,
  md: 10,
  pill: 999,
};
