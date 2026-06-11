//
//  ProgramEditorView.swift
//  GymApp
//
//  Program editor: metadata, week tabs, day picker, exercise targets, activate
//  sheet, per-muscle volume inspector. Designed to the editorial system +
//  08.03 spec (no prototype frame). Editing behavior is visual only.
//

import SwiftUI

struct ProgramEditorView: View {
    @Environment(\.editorialAccent) private var accent
    @State private var week = "W4"
    @State private var dayIndex = 0
    @State private var showActivate = false
    @State private var showVolume = false

    private var days: [MockData.ProgramDay] { MockData.sampleWeek }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                metadata
                weekTabs
                dayPicker
                dayEditor
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("Edit program")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Activate") { showActivate = true }
                    .fontWeight(.semibold)
                    .foregroundStyle(accent)
            }
        }
        .safeAreaInset(edge: .bottom) { volumeInspector }
        .sheet(isPresented: $showActivate) { activateSheet }
    }

    // MARK: Metadata

    private var metadata: some View {
        VStack(alignment: .leading, spacing: 10) {
            editableField(label: "Name", value: "PPL — Vanilla 6-day")
            HStack(spacing: 24) {
                editableField(label: "Goal", value: "Hypertrophy")
                editableField(label: "Days / week", value: "6")
            }
        }
        .padding(.horizontal, 24)
        .padding(.top, 8)
        .padding(.bottom, 20)
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }

    private func editableField(label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).kicker()
            HStack(spacing: 6) {
                Text(value).font(.title2Serif).foregroundStyle(.ink)
                Image(systemName: "pencil").font(.system(size: 12)).foregroundStyle(.ink3)
            }
        }
    }

    // MARK: Week tabs

    private var weekTabs: some View {
        ScrollView(.horizontal) {
            UnderlineSegmented(
                selection: $week,
                options: MockData.weekTabs.map { ($0, $0) },
                spacing: 16
            )
            .padding(.horizontal, 20)
        }
        .scrollIndicators(.hidden)
        .padding(.vertical, 16)
    }

    // MARK: Day picker

    private var dayPicker: some View {
        HStack(spacing: 8) {
            ForEach(Array(days.enumerated()), id: \.element.id) { index, day in
                Button {
                    dayIndex = index
                } label: {
                    Text(day.name)
                        .font(.system(size: 12, weight: .semibold))
                        .textCase(.uppercase).tracking(0.8)
                        .foregroundStyle(index == dayIndex ? .bg : .ink2)
                        .padding(.horizontal, 14).padding(.vertical, 7)
                        .background {
                            if index == dayIndex {
                                Capsule().fill(Color.ink)
                            } else {
                                Capsule().stroke(Color.hairline, lineWidth: 1)
                            }
                        }
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 16)
    }

    // MARK: Day editor

    private var dayEditor: some View {
        let day = days[dayIndex]
        return VStack(spacing: 0) {
            Rectangle().fill(Color.hairline).frame(height: 1)
            ForEach(Array(day.exercises.enumerated()), id: \.element.id) { index, ex in
                HStack(spacing: 12) {
                    Image(systemName: "line.3.horizontal")
                        .font(.system(size: 14)).foregroundStyle(.ink3)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(ex.name).font(.bodyText).foregroundStyle(.ink)
                        Text(ex.target).font(.caption).monospacedDigit().foregroundStyle(.ink2)
                    }
                    Spacer(minLength: 8)
                    Image(systemName: "chevron.right")
                        .font(.system(size: 13, weight: .semibold)).foregroundStyle(.ink3)
                }
                .frame(minHeight: 52)
                .padding(.vertical, 4)
                if index < day.exercises.count - 1 {
                    Rectangle().fill(Color.hairline).frame(height: 1)
                }
            }
            Rectangle().fill(Color.hairline).frame(height: 1)

            Button { } label: {
                Text("+ Add exercise")
                    .font(.system(size: 14)).foregroundStyle(.ink2)
                    .frame(maxWidth: .infinity).padding(.vertical, 12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(style: StrokeStyle(lineWidth: 1, dash: [4]))
                            .foregroundStyle(.ink3))
            }
            .buttonStyle(.plain)
            .padding(.top, 12)
        }
        .padding(.horizontal, 20)
    }

    // MARK: Volume inspector (collapsible)

    private var volumeInspector: some View {
        VStack(spacing: 0) {
            Button {
                withAnimation(.snappy) { showVolume.toggle() }
            } label: {
                HStack {
                    Text("Per-muscle volume").font(.system(size: 13, weight: .semibold)).foregroundStyle(.ink)
                    EditorialChip(text: "2 below target", tone: .warning)
                    Spacer()
                    Image(systemName: showVolume ? "chevron.down" : "chevron.up")
                        .font(.system(size: 12, weight: .semibold)).foregroundStyle(.ink3)
                }
                .padding(.horizontal, 20).padding(.vertical, 12)
            }
            .buttonStyle(.plain)

            if showVolume {
                VStack(spacing: 0) {
                    ForEach(MockData.muscleVolumes.prefix(6)) { m in
                        HStack {
                            Text(m.name).font(.caption).foregroundStyle(.ink2)
                            Spacer()
                            Text("\(m.sets) / \(m.target)")
                                .font(.caption).monospacedDigit()
                                .foregroundStyle(m.sets < m.target ? .warning : .ink)
                        }
                        .padding(.horizontal, 20).padding(.vertical, 5)
                    }
                }
                .padding(.bottom, 8)
            }
        }
        .background(.thinMaterial)
        .overlay(alignment: .top) { Divider().overlay(Color.hairline) }
    }

    // MARK: Activate sheet

    private var activateSheet: some View {
        NavigationStack {
            Form {
                Section {
                    DatePicker("Start date", selection: .constant(.now), displayedComponents: .date)
                    Picker("Starting weekday", selection: .constant("Monday")) {
                        ForEach(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], id: \.self) {
                            Text($0)
                        }
                    }
                }
                Section {
                    Toggle("Shift remaining program", isOn: .constant(true)).tint(.ink)
                } footer: {
                    Text("Reschedules later workouts to keep the program contiguous.")
                }
            }
            .navigationTitle("Activate program")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { showActivate = false }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Activate") { showActivate = false }.fontWeight(.semibold)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

#Preview {
    NavigationStack {
        ProgramEditorView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
