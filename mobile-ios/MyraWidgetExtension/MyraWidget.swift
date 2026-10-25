import SwiftUI
import WidgetKit

private struct MyraWidgetEntry: TimelineEntry {
    let date: Date
    let state: String
    let stepNumber: Int
    let totalSteps: Int
    let lastUpdated: Date?

    var stateLabel: String {
        switch state.lowercased() {
        case "running", "executing", "executando": return "Executando"
        case "done", "completed", "concluida", "concluído": return "Concluída"
        case "error", "failed", "erro": return "Com erro"
        case "paused", "pausada": return "Pausada"
        case "cancelled", "canceled", "cancelada": return "Cancelada"
        case "idle": return "Pronta"
        default: return "Abra o app MYRA"
        }
    }
}

private enum MyraWidgetStore {
    static func currentEntry() -> MyraWidgetEntry {
        let shared = UserDefaults(suiteName: "group.com.myra.mobile")
        return MyraWidgetEntry(
            date: Date(),
            state: shared?.string(forKey: "myra.widget.state") ?? "unconfigured",
            stepNumber: shared?.integer(forKey: "myra.widget.stepNumber") ?? 0,
            totalSteps: shared?.integer(forKey: "myra.widget.totalSteps") ?? 0,
            lastUpdated: {
                let value = shared?.double(forKey: "myra.widget.updatedAt") ?? 0
                return value > 0 ? Date(timeIntervalSince1970: value) : nil
            }()
        )
    }
}

private struct MyraWidgetProvider: TimelineProvider {
    func placeholder(in context: Context) -> MyraWidgetEntry {
        MyraWidgetEntry(date: Date(), state: "running", stepNumber: 2, totalSteps: 5, lastUpdated: Date())
    }

    func getSnapshot(in context: Context, completion: @escaping (MyraWidgetEntry) -> Void) {
        completion(MyraWidgetStore.currentEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<MyraWidgetEntry>) -> Void) {
        let entry = MyraWidgetStore.currentEntry()
        completion(Timeline(entries: [entry], policy: .after(Date().addingTimeInterval(15 * 60))))
    }
}

private struct MyraWidgetView: View {
    let entry: MyraWidgetEntry
    @Environment(\.widgetFamily) private var family

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("MYRA", systemImage: "sparkles")
                .font(.headline)
            Text(entry.stateLabel)
                .font(family == .accessoryRectangular ? .caption : .title3)
                .fontWeight(.semibold)
                .lineLimit(1)
            if entry.totalSteps > 0 && family != .accessoryRectangular {
                Text("Passo \(entry.stepNumber) de \(entry.totalSteps)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
            if let lastUpdated = entry.lastUpdated {
                Text("Atualizado \(lastUpdated, style: .time)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            } else {
                Text("Conecte pelo app")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .containerBackground(.fill.tertiary, for: .widget)
    }
}

@main
struct MyraWidget: Widget {
    private let kind = "MyraWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: MyraWidgetProvider()) { entry in
            MyraWidgetView(entry: entry)
        }
        .configurationDisplayName("MYRA Control")
        .description("Veja o estado atual da MYRA no computador.")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular])
    }
}
