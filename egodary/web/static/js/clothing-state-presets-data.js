/* Built-in quick states for outfit clothing modifiers */
window.CLOTHING_STATE_PRESETS = [
  {
    id: "cs_wet_torn",
    label: "Wet + Torn",
    hint: "Soaked · Ripped",
    conditions: { moisture: "wet_soaked", damage: "torn_ripped" },
  },
  {
    id: "cs_wet_see_through",
    label: "Wet see-through",
    hint: "Soaked · See-through",
    conditions: { moisture: "wet_soaked", transparency: "see_through" },
  },
  {
    id: "cs_rain_soaked",
    label: "Rain soaked",
    hint: "Soaked · Water droplets · Clinging",
    conditions: { moisture: "wet_soaked", extra: "water_droplets", fit: "clinging" },
  },
  {
    id: "cs_post_fight",
    label: "After fight",
    hint: "Heavily damaged · Torn · Disheveled",
    conditions: { damage: "heavily_damaged", disorder: "disheveled_messy" },
  },
  {
    id: "cs_sleep_messy",
    label: "Just woke up",
    hint: "Rumpled · Half-undone",
    conditions: { disorder: "rumpled_wrinkled", partial_removal: "half_undone" },
  },
  {
    id: "cs_tight_wet",
    label: "Tight & wet",
    hint: "Soaked · Clinging",
    conditions: { moisture: "wet_soaked", fit: "clinging" },
  },
  {
    id: "cs_sheer_wet",
    label: "Sheer wet",
    hint: "Wet see-through",
    conditions: { transparency: "wet_see_through" },
  },
  {
    id: "cs_partial_undress",
    label: "Partial undress",
    hint: "Partially removed · Open",
    conditions: { partial_removal: "partially_removed", disorder: "half_undone" },
  },
  {
    id: "cs_sweat_workout",
    label: "Workout sweat",
    hint: "Sweat-soaked · Sweat-stained",
    conditions: { moisture: "sweat_soaked", stains: "sweat_stained" },
  },
  {
    id: "cs_nsfw_after",
    label: "NSFW aftermath",
    hint: "Cum-stained · Disheveled · Partially removed",
    conditions: { stains: "cum_stained", disorder: "disheveled_messy", partial_removal: "partially_removed" },
  },
  {
    id: "cs_oil_shiny",
    label: "Oiled & shiny",
    hint: "Oil / shiny · Clinging",
    conditions: { extra: "oil_shiny", fit: "clinging" },
  },
  {
    id: "cs_slipping",
    label: "Slipping off",
    hint: "Slipping · Pulled down",
    conditions: { disorder: "slipping_off", partial_removal: "pulled_down" },
  },
];
