# kube-ml-runner 🚀

> A tiny Kubernetes project that runs a Python inference script as a **Job**, mounts folders from the host machine into the pod, and writes predictions back out to the host. Built as a personal learning project to understand what Kubernetes actually *is* — not to build anything production-grade.

---

## 🤔 What Does This Project Do?

In one sentence: **it runs a Python script inside a Kubernetes cluster, and lets that script read and write files on my laptop as if they were on the same machine.**

That's it. That's the whole thing.

The script is called `infer.py`. It:

1. Reads a "model" from `model/model.json` (a JSON lookup table — no real ML here, just a stand-in)
2. Reads questions from `data/input.jsonl`
3. Writes predictions to `output/predictions.jsonl`

But those three files don't live *inside* the cluster. They live on my laptop. Kubernetes, using a mechanism called `hostPath` + `extraMounts`, hands them to the pod as if they were local folders. The pod writes to `output/`, and that file shows up back on my laptop.

**Why does that matter?** Because that exact pattern — host folder → cluster pod → host folder — is how real ML batch pipelines work. Change `model.json` for a 5 GB checkpoint on S3, change `input.jsonl` for a Parquet file with 10 million rows, and you have a production workload.

---

## 🍳 The Kitchen Analogy (For When I Forget)

Imagine a restaurant.

| Kubernetes term | Kitchen equivalent |
|---|---|
| **Docker image** | A recipe card + all ingredients, frozen together |
| **Container** | That recipe being cooked *right now* in a kitchen |
| **Pod** | One chef working in one kitchen |
| **Job** | An order that says "make this one dish, then close the kitchen" |
| **Volume** | A pantry shelf the chef can grab ingredients from |
| **Cluster** | The whole restaurant building |
| **Node** | One physical kitchen in that building |
| **kubectl** | Me, shouting orders at the restaurant manager |
| **KinD** | A mini restaurant I built inside my own house |
| **namespace** | A section of the restaurant (e.g. "desserts", "grill") |

If I ever forget what a Pod is, I can re-read this table and be fine.

---

## 🗺️ The Big Picture

Here's what the whole thing looks like:

```text
┌───────────────────────────────────────────────────────────┐
│ MY LAPTOP (host machine)                                  │
│                                                           │
│ ~/kube-ml-runner/                                         │
│ ├── model/model.json   ← the "model"                      │
│ ├── data/input.jsonl   ← the questions                    │
│ ├── output/            ← predictions land here            │
│ ├── app/                                                  │
│ │   ├── Dockerfile     ← how to build the image           │
│ │   └── infer.py       ← the Python script                │
│ └── k8s/                                                  │
│     ├── pv.yaml        ← "a shelf exists here"            │
│     ├── pvc.yaml       ← "I need that shelf"              │
│     └── job.yaml       ← "run this container"             │
│                                                           │
│   ↕ extraMounts (hostPath)                                │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ KinD cluster (a container running K8s)              │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │ Pod: ml-inference-job-xxxxx                   │  │  │
│  │  │  ┌─────────────────────────────────────────┐  │  │  │
│  │  │  │ Container: ml-inference                 │  │  │  │
│  │  │  │ - /models ← mapped to model/            │  │  │  │
│  │  │  │ - /data   ← mapped to data/             │  │  │  │
│  │  │  │ - /output ← mapped to output/           │  │  │  │
│  │  │  │ - python infer.py                       │  │  │  │
│  │  │  └─────────────────────────────────────────┘  │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

The container thinks it's reading `/models/model.json`.
The cluster thinks it's reading `/mnt/model/model.json`.
The laptop knows it's actually reading `~/kube-ml-runner/model/model.json`.

**Three different paths, same file.** That's the trick.

---

## 📖 Terminology, In My Own Words

### 🧊 Container

A running process that's isolated from the rest of the machine. It has its own filesystem, its own network, its own everything. Built from an *image* (a frozen recipe).

Not a VM. Much lighter. Starts in milliseconds.

### 📦 Image

A frozen snapshot of a filesystem + a command to run. Written in a `Dockerfile`. Built with `docker build`. Stored in a registry (Docker Hub, ECR, etc.) or locally.

You can think of it as: **"Python 3.11 + my infer.py, zipped into a self-contained thing."**

### 🫛 Pod

The smallest unit Kubernetes schedules. Usually contains one container. It's like "one chef, one kitchen, one job."

Pods are **ephemeral** — they're meant to be thrown away and recreated. If you're thinking "this is my long-running server", you're thinking of a *Deployment*, not a Pod.

### 📋 Job

A controller that says: "run this pod until it succeeds, then stop." If the pod crashes, the Job restarts it (up to `backoffLimit` times). Once it completes, it's done.

Perfect for: batch ML inference, nightly data processing, one-shot migrations, training runs.

Not for: web servers, APIs (those use Deployments).

### 💾 Volume

A folder that gets mounted into a pod from somewhere else. The "somewhere else" could be:

- A host directory (`hostPath`)
- A cloud bucket (S3/GCS via CSI driver)
- An empty scratch space (`emptyDir`)
- A config file (ConfigMap)
- A secret (Secret)

The pod doesn't care where it comes from. It just sees a folder at a path you specify.

### 🗄️ PersistentVolume (PV)

A **declaration** that a piece of storage exists. It describes the storage, not who uses it. Like saying "there's a shelf at aisle 3, section B."

Written by: the cluster admin (or you, for a small setup).

### 📝 PersistentVolumeClaim (PVC)

A **request** for storage. The pod says "I need a read-only shelf of at least 1 GB." Kubernetes matches it against available PVs.

Written by: whoever owns the workload.

**Why two files instead of one?** Because in production, the person creating storage and the person consuming it are different people. The two-file design lets them negotiate without coordinating directly.

### 🏗️ Cluster

A bunch of machines (called **nodes**) that Kubernetes manages as one unit. You talk to the cluster through a single API endpoint, and it decides which node runs your pod.

### 🖥️ Node

One machine in the cluster. In a real cloud cluster, this might be an EC2 instance or a VM. In KinD, it's a Docker container pretending to be a machine.

### 🔧 kubectl

The CLI you use to talk to the cluster. Every command is basically a REST call to the Kubernetes API server. It's not magic — it's HTTP.

### 🐳 KinD (Kubernetes in Docker)

A tool that runs an entire Kubernetes cluster inside a single Docker container. Perfect for learning because you can spin one up and destroy it in seconds.

`kind create cluster` = "start a whole fake Kubernetes cluster on my laptop."

### 🧂 extraMounts (KinD-specific)

A KinD configuration option that says: "when you start the cluster, also bind-mount this host folder into the cluster's node container." Without it, `hostPath` volumes would point to empty dirs inside the node.

This is the glue between "my laptop's files" and "the cluster's files."

---

## 📂 The Files, One By One

### `app/infer.py` — the script that runs

```python
MODEL_PATH = "/models/model.json"
DATA_PATH  = "/data/input.jsonl"
OUTPUT_PATH = "/output/predictions.jsonl"
```

A simple Python script. When it runs:

1. Reads model JSON from `/models/model.json`
2. Reads questions from `/data/input.jsonl`
3. Writes predictions to `/output/predictions.jsonl`

It has zero awareness of Kubernetes. It just sees three folder paths. The infrastructure makes those paths work.

**Why this design is powerful:** the same script runs locally (`python infer.py`) or in a cluster. The paths don't change. Only what's mounted at those paths changes.

### `app/Dockerfile` — how to freeze the script

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY infer.py .
CMD ["python", "infer.py"]
```

Four lines. Read top to bottom:

- `FROM` — start with an official Python 3.11 image
- `WORKDIR` — switch to `/app` inside the image
- `COPY` — copy my `infer.py` into `/app/infer.py`
- `CMD` — when this container starts, run `python infer.py`

The output of `docker build` is a new image (my image) built on top of Python 3.11.

### `model/model.json` — the "model"

```json
{
  "What is 2+2?": "4",
  "What color is the sky?": "blue",
  "Capital of France?": "Paris"
}
```

In a real project, this would be neural network weights — 1 GB, 5 GB, 500 GB. In a toy project, it's a lookup table. The shape of the problem is the same: a big file the container reads.

### `data/input.jsonl` — the questions

```jsonl
{"question": "What is 2+2?"}
{"question": "What color is the sky?"}
{"question": "Capital of France?"}
{"question": "Unknown question"}
```

One JSON object per line. JSONL (JSON Lines) is a common format for ML pipelines because you can stream it without loading everything into memory.

### `k8s/pv.yaml` — "a shelf exists here"

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: model-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadOnlyMany
  hostPath:
    path: /mnt/model
```

Tells Kubernetes: "there's 1 GB of storage at `/mnt/model`, and many pods can read it at the same time."

Three of these exist (`model-pv`, `data-pv`, `output-pv`) because the pod needs three separate shelves.

### `k8s/pvc.yaml` — "I need that shelf"

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-pvc
spec:
  accessModes: [ReadOnlyMany]
  storageClassName: manual
  resources:
    requests:
      storage: 1Gi
```

Tells Kubernetes: "some pod is going to want a 1 GB read-only shelf. Please find one." Kubernetes matches this against the PVs from above, and binds them together.

### `k8s/job.yaml` — "cook this once, then stop"

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-inference-job
spec:
  backoffLimit: 2
  completions: 1
  parallelism: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: ml-inference
          image: ml-inference:latest
          imagePullPolicy: Never
          volumeMounts:
            - name: model
              mountPath: /models
              readOnly: true
            - name: data
              mountPath: /data
              readOnly: true
            - name: output
              mountPath: /output
      volumes:
        - name: model
          persistentVolumeClaim:
            claimName: model-pvc
        - name: data
          persistentVolumeClaim:
            claimName: data-pvc
        - name: output
          persistentVolumeClaim:
            claimName: output-pvc
```

This is the meat. Line-by-line:

| Line | Meaning |
|---|---|
| `kind: Job` | "This is a one-shot task, not a long-running service" |
| `backoffLimit: 2` | "If it crashes, retry twice, then give up" |
| `completions: 1` | "One successful run is enough" |
| `parallelism: 1` | "Don't run multiple copies at the same time" |
| `restartPolicy: Never` | "If the container crashes, don't restart it — let the Job controller make a new pod" |
| `image: ml-inference:latest` | "Use this image" |
| `imagePullPolicy: Never` | "Don't look for it in a registry — it's already in the cluster" |
| `volumeMounts:` | "Attach the following shelves to the container at these paths" |
| `volumes:` | "Here's which PVC provides each shelf" |

### `cluster-config.yaml` — the mini-restaurant's floor plan

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ml-runner
nodes:
  - role: control-plane
    extraMounts:
      - hostPath: /workspaces/kube-ml-runner/model
        containerPath: /mnt/model
      - hostPath: /workspaces/kube-ml-runner/data
        containerPath: /mnt/data
      - hostPath: /workspaces/kube-ml-runner/output
        containerPath: /mnt/output
```

This is what makes KinD see my host folders. Every `hostPath: /mnt/model` inside a PV resolves to the real `/workspaces/kube-ml-runner/model` on my laptop.

Without this file, `/mnt/model` inside the cluster would be a random empty directory.

---

## ⌨️ The Commands, Explained

Here's the full sequence, in order:

### 1. `kind create cluster --config cluster-config.yaml`

**What it does:** Spins up a whole Kubernetes cluster inside one Docker container.

**What it needs:** The `cluster-config.yaml` file — this tells KinD what mounts to set up.

**What "success" looks like:**

```text
Creating cluster "ml-runner" ...
 ✓ Ensuring node image (kindest/node:v1.31.0) 🖼
 ✓ Preparing nodes 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-ml-runner"
```

**Takes about:** 30–60 seconds the first time, ~10 seconds after that (image cached).

### 2. `kubectl get nodes`

**What it does:** Lists the machines in the cluster.

**Expected output:**

```text
NAME                      STATUS   ROLES           AGE   VERSION
ml-runner-control-plane   Ready    control-plane   30s   v1.31.0
```

**Why run it:** Sanity check. If `STATUS` isn't `Ready`, stop — don't proceed.

### 3. `docker build -t ml-inference:latest app/`

**What it does:** Reads `app/Dockerfile` and builds an image.

- `-t ml-inference:latest` = tag the image with that name.
- `app/` = the **build context** — the folder containing the Dockerfile and any files it `COPY`s.

**Where the image lives afterward:** In my local Docker image store. Kubernetes cannot see it yet.

### 4. `kind load docker-image ml-inference:latest --name ml-runner`

**What it does:** Copies the image from local Docker into the KinD cluster's internal Docker store.

**Why this exists:** Kubernetes doesn't have access to my laptop's Docker images. They need to be transferred across the boundary. This is the bridge.

**Analogy:** like mailing a recipe card to the mini restaurant.

**Why `imagePullPolicy: Never` in the Job:** because I told Kubernetes "don't pull from a registry, the image is already here." If I forget to run `kind load`, the Job will fail with `ErrImageNeverPull`.

### 5. `kubectl apply -f k8s/pv.yaml`

**What it does:** Reads the file and tells Kubernetes "make it so."

**Result:** `persistentvolume/model-pv created`

**Why:** Kubernetes is *declarative*. You describe the desired state, it figures out how to reach it.

### 6. `kubectl apply -f k8s/pvc.yaml`

Same idea. Tells Kubernetes "someone will be requesting these shelves." Kubernetes matches each PVC to a PV.

**Result:** `persistentvolumeclaim/model-pvc created`

### 7. `kubectl apply -f k8s/job.yaml`

Tells Kubernetes "run this container, once."

**Result:** `job.batch/ml-inference-job created`

Kubernetes now:

1. Creates a Pod
2. Assigns it to a node
3. Pulls the image (locally — `imagePullPolicy: Never`)
4. Binds the PVCs as volumes
5. Runs `python infer.py`
6. Watches for exit

### 8. `kubectl get pods -w`

**What it does:** Lists pods and follows changes (`-w` = watch).

**Expected progression:**

```text
ml-inference-job-xxxxx   0/1   Pending            0   0s
ml-inference-job-xxxxx   0/1   ContainerCreating  0   1s
ml-inference-job-xxxxx   1/1   Running            0   4s
ml-inference-job-xxxxx   0/1   Completed          0   12s
```

**Statuses mean:**

- `Pending` — waiting for a node to accept it
- `ContainerCreating` — pulling image, mounting volumes
- `Running` — container executing
- `Completed` — exited with code 0 ✅
- `Error` — exited with non-zero code ❌

Press `Ctrl+C` to stop watching after `Completed`.

### 9. `kubectl logs job/ml-inference-job`

**What it does:** Retrieves the container's stdout.

**Why:** The container is gone (it completed). But Kubernetes keeps its logs. This is the only way to see what it printed.

**Expected output:**

```text
Loaded model with 3 entries
Processing 4 records
Wrote 4 predictions to /output/predictions.jsonl
```

### 10. `cat output/predictions.jsonl`

**What it does:** Reads a file — but on my laptop, not inside the cluster.

**Why this is the payoff:** The container wrote to `/output/` inside its own filesystem. But because of the PVC → hostPath → extraMounts chain, the file landed on my laptop's disk. This is proof the round-trip works.

**Expected output:**

```text
{"question": "What is 2+2?", "prediction": "4"}
{"question": "What color is the sky?", "prediction": "blue"}
{"question": "Capital of France?", "prediction": "Paris"}
{"question": "Unknown question", "prediction": "unknown"}
```

---

## 🧹 Cleanup

```bash
kind delete cluster --name ml-runner
```

Deletes the whole cluster. All pods, volumes, and images inside disappear.

**But:** files written to `output/` on my laptop stay. That's the whole point.

---

## 🏭 Real-World Use Cases

This pattern — "run a script, read files from storage, write results back" — is called **batch inference** (or batch processing). It's how a huge amount of production ML runs.

Concrete examples:

### 🏦 Banking: Nightly fraud detection

A bank has 10 million customer records. Every night at 2 AM, a CronJob:

1. Mounts yesterday's transaction data from S3
2. Loads a fraud-detection model
3. Scores each customer
4. Writes flagged transactions to a database
5. Exits

Same skeleton as this project. Just bigger numbers.

### 🖼️ Healthcare: Bulk medical imaging

A company receives 50,000 X-rays per day:

1. Files land in cloud storage
2. A Job spins up on Kubernetes
3. Mounts the batch via a CSI driver (S3-compatible)
4. Runs a segmentation model on each
5. Writes annotations back to storage
6. Exits

### 🧠 LLM fine-tuning

Every custom fine-tune of an open-source model:

1. Mount the training data
2. Mount a base model checkpoint
3. Train LoRA weights
4. Save them
5. Exit

(This is literally what I did in the KubeEdge Ianvs example — same pattern, different scale.)

### 🎬 Media: Video transcoding

Netflix-style pipelines, where a new episode needs to be transcoded into 20 different formats. Each format = a Job. Same pattern.

### 🌐 Web scraping

Scrape 1M product pages:

1. Input list of URLs
2. Job fans out, scraping in parallel
3. Writes data to a database
4. Exits

---

## 🎓 Why I Built This

I'm an AI/ML engineer. I picked Kubernetes because:

1. **Most LFX mentorship orgs are Kubernetes-adjacent.** If I want to contribute to CNCF projects, I need to not be intimidated by pods and PVCs.
2. **ML infra in production runs on Kubernetes.** If I ever join an MLOps team, this is table stakes.
3. **It's a good vibe check.** Can I learn something completely outside my comfort zone in a few hours? Turns out yes.

This project is small on purpose. I'm not trying to build a real ML pipeline — I'm trying to internalize what a pod, a Job, and a volume actually are, so that when I read a production manifest, I don't get lost.

**Mission accomplished.**

---

## 🐛 Bugs I Hit (And What They Taught Me)

### ❌ `DOCKERFILE` vs `Dockerfile`

Docker looks for a file literally named `Dockerfile` — capital D, lowercase rest. I accidentally wrote `DOCKERFILE` (all caps). Docker couldn't find it.

**Lesson:** filenames are case-sensitive on Linux.

### ❌ Nested `kube-ml-runner/kube-ml-runner/`

My `cluster-config.yaml` pointed to `/workspaces/kube-ml-runner/kube-ml-runner/model` — a doubled path. KinD created that nested directory as root, mount-locked it, and then `rm` couldn't touch it.

**Lesson:** Always double-check paths. When KinD (or Docker) creates a hostPath target that doesn't exist, it makes it as root. And if the cluster is running, the mount is locked.

**Fix:** `kind delete cluster` first, then `sudo rm -rf` the stray dir.

### ❌ `ErrImageNeverPull`

I set `imagePullPolicy: Never` in `job.yaml` but forgot to run `kind load docker-image`. The Job kept creating pods that couldn't find the image.

**Lesson:** `imagePullPolicy: Never` is a promise. If you break that promise, the pod fails with `ErrImageNeverPull` — meaning "you told me it's here, and it's not."

### ❌ `connection refused` from kubectl

After a partial cluster delete, `kubectl` was still pointing at a dead API server. Every command failed with `dial tcp 127.0.0.1:... connection refused`.

**Lesson:** `kind delete cluster` usually cleans up the kubectl context, but not always. If `kubectl` can't reach the server, check `kubectl config get-contexts` and clean the stale context manually.

---

## 🚦 What I Would Do Next (If I Kept Going)

Just to have these on record:

1. **Swap the toy model for a real one** — add `transformers` to a `requirements.txt`, use `pipeline("sentiment-analysis")` in `infer.py`, rebuild. This would teach me image size limits and model download behavior inside clusters.
2. **Add a Kubernetes Secret** — to pass an API key into the pod without baking it into the image. Perfect for calling OpenAI / Anthropic instead of loading a local model.
3. **Parallelize** — change `completions: 3`. Watch three pods run at once. Now I have to shard the input by pod index. This teaches distributed batch processing.
4. **Add a CronJob** — instead of running once, run nightly. Now it's a real production pattern.
5. **Convert to a Deployment + Service** — the "serving" pattern instead of "batch." Pods run 24/7, respond to HTTP requests.
6. **Add Prometheus metrics** — see how long the job takes, how much memory it used, etc.

Each of these is a small change with a big learning payoff. But none of them are required to understand what Kubernetes *is*. That's already done.

---

## 📌 TL;DR

- This project runs a Python script inside Kubernetes as a **Job**.
- It mounts host folders into the pod using `hostPath` + `extraMounts` + `PersistentVolumeClaim`.
- The script reads from `/models` and `/data`, writes to `/output`, and those paths are really my laptop's folders.
- The pattern is called **batch inference** and is how a huge amount of production ML runs.
- I built it to not be intimidated by Kubernetes when contributing to CNCF projects.

I don't know everything about Kubernetes. But I know enough.

---

*Built during a rainy weekend in 2026 while trying to learn what a Pod actually is. Turns out it's just a chef in a kitchen.* 👨‍🍳