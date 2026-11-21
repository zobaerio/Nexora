// NEXORA — Nexora.Target.cs (game target, Windows 64-bit)
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

using UnrealBuildTool;
using System.Collections.Generic;

public class NexoraTarget : TargetRules
{
	public NexoraTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("Nexora");
	}
}
