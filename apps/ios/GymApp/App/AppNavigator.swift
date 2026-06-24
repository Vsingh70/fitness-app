//
//  AppNavigator.swift
//  GymApp
//
//  Lightweight cross-tab navigation seam. The tab shell owns the selected tab;
//  surfaces (e.g. an Insights card) drive a cross-tab deep link by writing here
//  rather than reaching into the shell's private `@State`. Mirrors the web
//  Insights deep links: program-shaped insights jump to the Programs spine
//  ("Adjust program"), exercise-shaped insights open the exercise analytics.
//  Programs + the exercise analytics both live inside the Workouts tab's
//  `NavigationStack`, so a deep link selects that tab and queues a route the
//  Workouts surface drains on appear.
//

import SwiftUI

@MainActor
@Observable
final class AppNavigator {
    /// The five top-level tabs the shell's `TabView` binds to.
    enum Tab: Hashable { case today, workouts, nutrition, insights, settings }

    /// A route the Workouts tab should push once selected. The shell's Workouts
    /// stack drains this; mirrors the web routes `/exercises/{id}` and `/programs`.
    enum WorkoutsDeepLink: Equatable { case exerciseDetail, programs }

    /// The currently selected tab. The shell binds its `TabView` to this.
    var tab: Tab = .today

    /// A queued deep link into the Workouts tab's stack, consumed once.
    var pendingWorkoutsLink: WorkoutsDeepLink?

    /// Deep-link to the exercise analytics (insight carrying an `exercise_id`).
    func openExercise() {
        pendingWorkoutsLink = .exerciseDetail
        tab = .workouts
    }

    /// Deep-link to the Programs spine ("Adjust program").
    func openPrograms() {
        pendingWorkoutsLink = .programs
        tab = .workouts
    }
}
