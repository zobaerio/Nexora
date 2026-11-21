// NEXORA — Nexora.cpp (module implementation)
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

#include "Nexora.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY(LogNexora);

class FNexoraModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		UE_LOG(LogNexora, Log, TEXT("NEXORA module started."));
	}

	virtual void ShutdownModule() override
	{
		UE_LOG(LogNexora, Log, TEXT("NEXORA module shut down."));
	}
};

IMPLEMENT_PRIMARY_GAME_MODULE(FNexoraModule, Nexora, "Nexora");
