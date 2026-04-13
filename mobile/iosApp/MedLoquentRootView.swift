import SwiftUI
import MedLoquentShared

struct MedLoquentRootView: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        MedLoquentIosHost().rootViewController()
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {
    }
}
