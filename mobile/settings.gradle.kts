pluginManagement {
    repositories {
        google()
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "medloquent"

include(":androidApp")
include(":shared:core")
include(":shared:audio")
include(":shared:asr")
include(":shared:nlp")
include(":shared:ehr")
include(":shared:crypto")
include(":shared:storage")
include(":shared:fl")
include(":shared:lora")
include(":shared:app")
