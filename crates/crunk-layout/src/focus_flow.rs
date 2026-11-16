//! The focus graph across scenes: each scene's own [`FocusGraph`] plus the scene-to-scene
//! transitions a flow declares between screens, so reachability and traps can be judged across
//! the whole project and not one scene at a time.
//!
//! A scene is one node of the atlas. Entry scenes are those no other scene transitions into (a
//! project whose scenes all sit on a cycle enters at the first). A scene with no outgoing
//! transition ends the flow (an exit), which is not a trap; a scene whose transitions only loop
//! among scenes that never lead back to an entry is.

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW

use std::collections::{BTreeSet, VecDeque};

use crate::focus::FocusGraph;

/// One scene of the atlas: its name (the screen id it renders) and its own focus graph.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AtlasScene {
    /// The scene name, which a flow node's screen id is matched against.
    pub name: String,
    /// The focus graph inside this scene.
    pub graph: FocusGraph,
}

/// A transition a flow names whose end is not a scene of the atlas.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DanglingTransition {
    /// The screen the transition leaves.
    pub from: String,
    /// The screen the transition enters.
    pub to: String,
}

/// The focus graphs of every scene joined by the flows' scene-to-scene transitions.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct FocusAtlas {
    /// The scenes, in the order given.
    pub scenes: Vec<AtlasScene>,
    /// Scene-to-scene moves (indices into [`FocusAtlas::scenes`]), sorted, self moves dropped.
    pub links: Vec<(usize, usize)>,
    /// Transitions that name a screen no scene renders.
    pub dangling: Vec<DanglingTransition>,
}

impl FocusAtlas {
    /// Join `scenes` by `transitions`, each a (from screen id, to screen id) pair.
    pub fn new(scenes: Vec<AtlasScene>, transitions: &[(String, String)]) -> Self {
        let index_of = |name: &str| scenes.iter().position(|s| s.name == name);
        let mut links: BTreeSet<(usize, usize)> = BTreeSet::new();
        let mut dangling = Vec::new();
        for (from, to) in transitions {
            match (index_of(from), index_of(to)) {
                (Some(a), Some(b)) if a != b => {
                    links.insert((a, b));
                }
                (Some(_), Some(_)) => {}
                _ => dangling.push(DanglingTransition {
                    from: from.clone(),
                    to: to.clone(),
                }),
            }
        }
        tracing::debug!(
            scenes = scenes.len(),
            links = links.len(),
            dangling = dangling.len(),
            "focus atlas built"
        );
        Self {
            scenes,
            links: links.into_iter().collect(),
            dangling,
        }
    }

    /// The scenes the flow starts in: those nothing transitions into, else the first scene.
    pub fn entries(&self) -> Vec<usize> {
        let entered: BTreeSet<usize> = self.links.iter().map(|&(_, to)| to).collect();
        let roots: Vec<usize> = (0..self.scenes.len())
            .filter(|i| !entered.contains(i))
            .collect();
        if roots.is_empty() && !self.scenes.is_empty() {
            vec![0]
        } else {
            roots
        }
    }

    /// Scenes with focusable controls that no chain of transitions reaches from an entry scene.
    pub fn unreachable_scenes(&self) -> Vec<usize> {
        let seen = self.flood(&self.entries(), false);
        (0..self.scenes.len())
            .filter(|&i| !seen[i] && !self.scenes[i].graph.nodes.is_empty())
            .collect()
    }

    /// Reachable scenes with focusable controls that do transition onward, yet from which no chain
    /// of transitions returns to an entry scene: the pad circles among scenes with no way out.
    /// A scene with no outgoing transition ends the flow and is not reported.
    pub fn stranded_scenes(&self) -> Vec<usize> {
        let entries = self.entries();
        let forward = self.flood(&entries, false);
        let back = self.flood(&entries, true);
        (0..self.scenes.len())
            .filter(|&i| {
                let g = &self.scenes[i].graph;
                forward[i]
                    && !back[i]
                    && self.links.iter().any(|&(from, _)| from == i)
                    && g.nodes.len() > g.modal_nodes.len()
            })
            .collect()
    }

    /// Breadth-first reach over scenes from `starts`, along links or (`reverse`) against them.
    fn flood(&self, starts: &[usize], reverse: bool) -> Vec<bool> {
        let mut seen = vec![false; self.scenes.len()];
        let mut queue: VecDeque<usize> = VecDeque::new();
        for &s in starts {
            if !seen[s] {
                seen[s] = true;
                queue.push_back(s);
            }
        }
        while let Some(n) = queue.pop_front() {
            for &(a, b) in &self.links {
                let (from, to) = if reverse { (b, a) } else { (a, b) };
                if from == n && !seen[to] {
                    seen[to] = true;
                    queue.push_back(to);
                }
            }
        }
        seen
    }
}
