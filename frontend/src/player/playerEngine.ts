import { Platform } from 'react-native';
import { Video, AVPlaybackStatus } from 'expo-av';


class PlayerEngine {
    private videoRef: { current: Video | null } = { current: null };
    private webVideoRef: { current: HTMLVideoElement | null } = { current: null };
    private statusListeners: Array<(status: AVPlaybackStatus) => void> = [];
    private _sourceUri: string | null = null;
    private _onSourceChange: ((uri: string | null) => void) | null = null;

    private get isWeb() {
        return Platform.OS === 'web';
    }

    getRef() {
        return this.videoRef;
    }

    getWebRef() {
        return this.webVideoRef;
    }

    setWebVideoElement(el: HTMLVideoElement | null) {
        this.webVideoRef.current = el;
    }

    // Web player listens for source changes through this callback.
    onSourceChange(cb: (uri: string | null) => void) {
        this._onSourceChange = cb;
    }

    getSourceUri() {
        return this._sourceUri;
    }

    addListener(callback: (status: AVPlaybackStatus) => void) {
        this.statusListeners.push(callback);
    }

    removeListener(callback: (status: AVPlaybackStatus) => void) {
        this.statusListeners = this.statusListeners.filter(l => l !== callback);
    }

    onStatusUpdate = (status: AVPlaybackStatus) => {
        this.statusListeners.forEach(listener => listener(status));
    };

    async play() {
        if (this.isWeb) {
            const el = this.webVideoRef.current;
            if (el) {
                try { await el.play(); } catch (_) { /* autoplay may be blocked */ }
            }
            return;
        }
        const ref = this.videoRef.current;
        if (ref) {
            try { await ref.playAsync(); } catch (e) {}
        }
    }

    async pause() {
        if (this.isWeb) {
            const el = this.webVideoRef.current;
            if (el) el.pause();
            return;
        }
        const ref = this.videoRef.current;
        if (ref) {
            try { await ref.pauseAsync(); } catch (e) {}
        }
    }

    async togglePlayPause() {
        if (this.isWeb) {
            const el = this.webVideoRef.current;
            if (!el) return;
            if (el.paused) {
                try { await el.play(); } catch (_) { /* autoplay blocked */ }
            } else {
                el.pause();
            }
            return;
        }

        const ref = this.videoRef.current;
        if (!ref) return;
        try {
            const status = await ref.getStatusAsync();
            if (!status.isLoaded) return;
            if (status.isPlaying) {
                await ref.pauseAsync();
            } else {
                await ref.playAsync();
            }
        } catch (e) {}
    }

    async seekTo(seconds: number) {
        if (!isFinite(seconds) || seconds < 0) return;

        if (this.isWeb) {
            const el = this.webVideoRef.current;
            if (el) el.currentTime = seconds;
            return;
        }
        const ref = this.videoRef.current;
        if (!ref) return;
        try { await ref.setPositionAsync(Math.round(seconds * 1000)); } catch (e) {}
    }

    async setPlaybackRate(rate: number) {
        if (this.isWeb) {
            const el = this.webVideoRef.current;
            if (el) el.playbackRate = rate;
            return;
        }
        const ref = this.videoRef.current;
        if (ref) {
            try { await ref.setRateAsync(rate, true); } catch (e) {}
        }
    }

    async setVolume(volume: number) {
        if (this.isWeb) {
            const el = this.webVideoRef.current;
            if (el) el.volume = Math.max(0, Math.min(1, volume));
            return;
        }
        const ref = this.videoRef.current;
        if (ref) {
            try { await ref.setVolumeAsync(volume); } catch (e) {}
        }
    }

    async load(uri: string) {
        this._sourceUri = uri;

        if (this.isWeb) {
            this._onSourceChange?.(uri);
            return;
        }
        const ref = this.videoRef.current;
        if (ref) {
            try { await ref.loadAsync({ uri }); } catch (e) {}
        }
    }

    async unload() {
        this._sourceUri = null;

        if (this.isWeb) {
            const el = this.webVideoRef.current;
            if (el) {
                el.pause();
                el.removeAttribute('src');
                el.load(); // reset the element
            }
            this._onSourceChange?.(null);
            return;
        }
        const ref = this.videoRef.current;
        if (ref) {
            try { await ref.unloadAsync(); } catch (e) {}
        }
    }
}

export const playerEngine = new PlayerEngine();
