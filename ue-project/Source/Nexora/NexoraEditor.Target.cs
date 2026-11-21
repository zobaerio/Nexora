// NEXORA — NexoraEditor.Target.cs (editor target)
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

using UnrealBuildTool;
using System.Collections.Generic;

public class NexoraEditorTarget : TargetRules
{
	public NexoraEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("Nexora");
	}
}
