# mod-template

Template for mods of Moorhuhn Kart: Open Source Edition. Clone it next to a checkout of mhk-os and run Tools/new-mod.py with a pack id and a title. Then open the project in Unity 6000.6.4f1, select the pack asset and build it with MHK > Modding > Build Selected Packs as Mods.

## Track variants

Tracks can offer variants: one option per modifier, such as direction (forward, reverse), time of day (day, night) and weather (clear, rain, snow, sandstorm). The game defines these modifiers and options (`TrackModifierDefinition`, `TrackOptionDefinition`), and a mod can add its own. A `TrackOverlayDefinition` makes a track offer an option, optionally with an overlay scene that loads on top of the track scene while the option is selected. The overlay scene's `Overlay` root carries a `TrackOverlay`, which changes the track's sun, fill lights, ambient light, fog (it can turn fog on for a track without it) and sky textures, and can turn textures round (`flipTextures`: speed pad arrows in reverse). Its children add objects such as rain, lamps or ramps; the game's weather prefabs (`Packages/org.mhkose.sdk/Prefabs/Weather`: Rain, Snow, Sandstorm) bring their own sound, and rain its thunder. Each track decides which options it offers: an ice track can offer snow and a desert a sandstorm instead of rain. Any mod can add overlays to any track. For one track and option, the overlay of the mod highest in the load order wins. Bump `contentVersion` of a track, kart or overlay when a change alters lap times; older records of it no longer count. Create and edit overlays with MHK > Tracks > Track Variants, which shows the track scene as a locked reference behind the overlay. The example oval offers reverse and a night overlay.

## License

MIT. Game assets belong to their respective owners. If there is a problem with any of them, message me and I will remove it.
