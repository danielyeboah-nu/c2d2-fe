pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // ATAK SDK AAR — place the SDK file at atak-plugin/libs/main.jar (or .aar)
        // Download from https://tak.gov/products/atak-civ  (free registration required)
        flatDir { dirs("libs") }
    }
}

rootProject.name = "C2D2ATAKPlugin"
include(":app")
