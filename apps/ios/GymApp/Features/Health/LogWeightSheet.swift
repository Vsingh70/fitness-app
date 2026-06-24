//
//  LogWeightSheet.swift
//  GymApp
//
//  Bottom sheet for logging a body weight, mirroring the web `LogWeightSheet`.
//  Numeric entry in the user's chosen unit; the store converts to kg for the
//  wire. Dismisses on a successful save.
//

import SwiftUI

struct LogWeightSheet: View {
    let unit: WeightUnit
    /// Async save closure (store.logWeight). Returns when the round-trip resolves.
    let onSave: (Double) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var text = ""
    @State private var isSaving = false
    @FocusState private var focused: Bool

    private var parsed: Double? {
        let normalized = text.replacingOccurrences(of: ",", with: ".")
        guard let v = Double(normalized), v > 0, v < 1000 else { return nil }
        return v
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Today’s weight").kicker()
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        TextField("0.0", text: $text)
                            .font(.figure)
                            .monospacedDigit()
                            .keyboardType(.decimalPad)
                            .focused($focused)
                            .foregroundStyle(.ink)
                        Text(unit.title)
                            .font(.title3)
                            .foregroundStyle(.ink2)
                    }
                    .padding(.bottom, 10)
                    .overlay(alignment: .bottom) {
                        Rectangle().fill(Color.ink).frame(height: 1.5)
                    }
                }

                Button {
                    guard let value = parsed else { return }
                    Task {
                        isSaving = true
                        await onSave(value)
                        isSaving = false
                        dismiss()
                    }
                } label: {
                    if isSaving {
                        ProgressView().tint(.bg)
                    } else {
                        Text("Save")
                    }
                }
                .buttonStyle(.editorialPrimary)
                .disabled(parsed == nil || isSaving)
                .opacity(parsed == nil ? 0.5 : 1)

                Spacer()
            }
            .padding(24)
            .background(Color.bg)
            .navigationTitle("Log weight")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }.tint(.ink)
                }
            }
            .onAppear { focused = true }
        }
        .presentationDetents([.height(280)])
        .presentationDragIndicator(.visible)
    }
}

#Preview {
    Color.bg.sheet(isPresented: .constant(true)) {
        LogWeightSheet(unit: .kg) { _ in }
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
