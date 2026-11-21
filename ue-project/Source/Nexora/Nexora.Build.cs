// NEXORA — Nexora.Build.cs
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3). See docs/PHASE1-BUILD-SHEET.md.

using UnrealBuildTool;

public class Nexora : ModuleRules
{
	public Nexora(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Core runtime modules every NEXORA system needs.
		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput", // The ONLY input system NEXORA uses (Phase 3).
			"UMG",           // HUD, menus, Environment Control Panel.
			"Slate",
			"SlateCore"
		});

		// Added at their phases — do NOT enable early (build sheet Step 6):
		//   "AIModule", "StateTreeModule", "GameplayStateTreeModule", "MassGameplay",
		//   "MassAIBehavior", "SmartObjectsModule", "ZoneGraph", "ChaosVehicles",
		//   "Water", "Niagara", "MetaHuman" — uncomment when the phase arrives.

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"RenderCore",
			"RHI"
		});
	}
}
