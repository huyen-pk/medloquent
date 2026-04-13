# Android app shell

androidApp is a thin launcher around the shared Compose Multiplatform UI.

MainActivity injects:

- filesDir.absolutePath as the local storage root
- a normalized manufacturer-model device identifier for federated update provenance
- an Android share-sheet bridge so generated FHIR bundles can be exported as JSON

The shared workflow lives in mobile/shared/app and can be reused by additional Android surfaces such as tablets or ruggedized clinician devices.
