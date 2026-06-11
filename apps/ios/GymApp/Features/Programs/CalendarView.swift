//
//  CalendarView.swift
//  GymApp
//
//  Month grid of scheduled workouts. Each day shows a workout chip; completed
//  in accent, today filled ink, future muted. Tap a day → scheduled-workout
//  sheet. Designed to the editorial system + 08.03 spec (no prototype frame).
//

import SwiftUI

struct CalendarView: View {
    @Environment(\.editorialAccent) private var accent
    @State private var selected: MockData.CalendarDay?

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 4), count: 7)

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                ScreenHeader(title: "Calendar", subtitle: MockData.calendarTitle)
                weekdayHeader
                grid
                legend
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $selected) { day in daySheet(day) }
    }

    private var weekdayHeader: some View {
        HStack(spacing: 4) {
            ForEach(Array(MockData.calendarWeekdays.enumerated()), id: \.offset) { _, wd in
                Text(wd)
                    .font(.system(size: 10, weight: .semibold)).tracking(0.5)
                    .foregroundStyle(.ink3)
                    .frame(maxWidth: .infinity)
            }
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 8)
    }

    private var grid: some View {
        LazyVGrid(columns: columns, spacing: 4) {
            ForEach(MockData.calendarDays) { day in
                if day.day == nil {
                    Color.clear.frame(height: 56)
                } else {
                    dayCell(day)
                        .onTapGesture { if day.workout != nil { selected = day } }
                }
            }
        }
        .padding(.horizontal, 16)
    }

    private func dayCell(_ day: MockData.CalendarDay) -> some View {
        let fg: Color = day.today ? .bg : (day.completed ? accent : (day.future ? .ink3 : .ink))
        return VStack(spacing: 3) {
            Text("\(day.day ?? 0)")
                .font(.system(size: 14, weight: .medium, design: .serif))
                .monospacedDigit()
                .foregroundStyle(fg)
            if let workout = day.workout {
                Text(workout)
                    .font(.system(size: 8, weight: .semibold))
                    .foregroundStyle(fg.opacity(0.9))
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            } else {
                Spacer().frame(height: 10)
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: 56)
        .background {
            if day.today {
                RoundedRectangle(cornerRadius: 3).fill(Color.ink)
            } else if day.workout != nil {
                RoundedRectangle(cornerRadius: 3).stroke(Color.hairline, lineWidth: 1)
            }
        }
    }

    private var legend: some View {
        HStack(spacing: 16) {
            legendItem(swatch: accent, label: "Completed")
            legendItem(swatch: .ink, label: "Today")
            legendItem(swatch: .ink3, label: "Upcoming")
        }
        .padding(.horizontal, 20)
        .padding(.top, 16)
    }

    private func legendItem(swatch: Color, label: String) -> some View {
        HStack(spacing: 6) {
            Circle().fill(swatch).frame(width: 8, height: 8)
            Text(label).font(.caption2).foregroundStyle(.ink2)
        }
    }

    private func daySheet(_ day: MockData.CalendarDay) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("\(MockData.calendarTitle.prefix(3)) \(day.day ?? 0)").kicker()
            Text(day.workout ?? "Rest day")
                .font(.titleSerif).foregroundStyle(.ink).padding(.top, 6)
            Text("5 exercises · ~58 min · 21 sets")
                .font(.footnote).foregroundStyle(.ink2).padding(.top, 4)

            if !day.completed {
                Button { selected = nil } label: { Label("Start workout", systemImage: "play.fill") }
                    .buttonStyle(.editorialPrimary).padding(.top, 20)
                Button("Reschedule") { selected = nil }
                    .buttonStyle(.editorialSecondary).padding(.top, 10)
            } else {
                Text("Completed").font(.headline).foregroundStyle(.success).padding(.top, 20)
            }
            Spacer()
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .presentationDetents([.medium])
    }
}

#Preview {
    NavigationStack {
        CalendarView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
