plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace         = "com.c2d2.atak"
    compileSdk        = 34
    ndkVersion        = "21.4.7075529"

    defaultConfig {
        applicationId  = "com.c2d2.atak"
        minSdk         = 21       // ATAK 4.x minimum
        targetSdk      = 34
        versionCode    = 1
        versionName    = "1.0.0"

        // Backend URL — override in local.properties or a build-flavour
        buildConfigField("String", "BACKEND_URL", "\"http://10.0.2.2:8000\"")
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions { jvmTarget = "11" }

    // ATAK plugins are signed APKs — configure your keystore in local.properties
    signingConfigs {
        create("release") {
            // storeFile     = file(project.findProperty("KEYSTORE_PATH") ?: "debug.keystore")
            // storePassword = project.findProperty("KEYSTORE_PASS") as String? ?: ""
            // keyAlias      = project.findProperty("KEY_ALIAS")      as String? ?: ""
            // keyPassword   = project.findProperty("KEY_PASS")       as String? ?: ""
        }
    }
}

dependencies {
    // ATAK SDK — place main.jar from the ATAK Plugin Development Kit in atak-plugin/libs/
    // https://tak.gov → Developer Resources → ATAK Plugin Development Kit
    compileOnly(fileTree(mapOf("dir" to "../libs", "include" to listOf("*.jar"))))

    // Networking
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // JSON
    implementation("com.google.code.gson:gson:2.10.1")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // AndroidX
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
}
