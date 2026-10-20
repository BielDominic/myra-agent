import SwiftUI

struct ContentView: View {
    @StateObject private var api = RemoteAPI()
    @State private var endpoint = UserDefaults.standard.string(forKey: "myra.remote.baseURL") ?? ""
    @State private var token = ""
    @State private var objective = ""
    @State private var showConnectionSettings = true

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    connectionCard
                    statusCard
                    taskCard
                    if let message = api.errorMessage, !message.isEmpty {
                        Text(message)
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(12)
                            .background(.red.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                    }
                }
                .padding()
            }
            .navigationTitle("MYRA")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await api.refreshStatus() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(!api.isConfigured || api.isBusy)
                    .accessibilityLabel("Atualizar status")
                }
            }
            .task {
                while !Task.isCancelled {
                    if api.isConfigured && !api.isBusy {
                        await api.refreshStatus()
                    }
                    try? await Task.sleep(nanoseconds: 5_000_000_000)
                }
            }
        }
    }

    private var connectionCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Conexao segura", systemImage: "lock.shield")
                    .font(.headline)
                Spacer()
                Button(showConnectionSettings ? "Ocultar" : "Configurar") {
                    withAnimation { showConnectionSettings.toggle() }
                }
                .font(.footnote)
            }

            if showConnectionSettings {
                TextField("https://pc.tailnet.ts.net/remote/v1", text: $endpoint)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    .autocorrectionDisabled()
                    .textFieldStyle(.roundedBorder)

                SecureField("Token remoto", text: $token)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textFieldStyle(.roundedBorder)

                Button {
                    do {
                        try api.saveConnection(baseURL: endpoint, token: token)
                        token = ""
                        showConnectionSettings = false
                        Task { await api.refreshStatus() }
                    } catch {
                        api.errorMessage = error.localizedDescription
                    }
                } label: {
                    Label("Salvar e conectar", systemImage: "checkmark.shield")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)

                Text("O token fica no Keychain do iPhone. Use HTTPS; nao compartilhe o token.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }

    private var statusCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Estado da MYRA", systemImage: "waveform.path")
                    .font(.headline)
                Spacer()
                Text(api.status?.state ?? "desconectada")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(stateColor.opacity(0.14), in: Capsule())
                    .foregroundStyle(stateColor)
            }

            if let status = api.status {
                if let objective = status.objective, !objective.isEmpty {
                    Text(objective).font(.subheadline.weight(.medium))
                }
                if let step = status.currentStep, !step.isEmpty {
                    Text(step).font(.footnote).foregroundStyle(.secondary)
                }
                if status.totalSteps > 0 {
                    ProgressView(value: Double(status.stepNumber), total: Double(max(status.totalSteps, 1)))
                    Text("Passo \(status.stepNumber) de \(status.totalSteps)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let result = status.result, !result.isEmpty {
                    Text(result).font(.subheadline)
                }
                if let error = status.error, !error.isEmpty {
                    Text(error).font(.footnote).foregroundStyle(.red)
                }
            } else {
                Text("Configure a conexao e toque em atualizar para consultar o computador.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }

    private var taskCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Nova tarefa", systemImage: "paperplane")
                .font(.headline)
            TextField("O que a MYRA deve fazer?", text: $objective, axis: .vertical)
                .lineLimit(3...6)
                .textFieldStyle(.roundedBorder)

            Button {
                let submitted = objective
                Task {
                    await api.startTask(objective: submitted)
                    if api.errorMessage == nil { objective = "" }
                }
            } label: {
                Label(api.isBusy ? "Aguarde..." : "Executar tarefa", systemImage: "play.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!api.isConfigured || api.isBusy || objective.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

            Button(role: .destructive) {
                Task { await api.cancelTask() }
            } label: {
                Label("Cancelar tarefa", systemImage: "stop.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .disabled(!api.isConfigured || api.isBusy || api.status?.state != "running")
        }
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }

    private var stateColor: Color {
        switch api.status?.state.lowercased() {
        case "running": return .orange
        case "done", "idle": return .green
        case "error": return .red
        default: return .secondary
        }
    }
}
