import React, { useCallback, useEffect } from 'react';
import { View, StyleSheet, Platform } from 'react-native';
import { Video, ResizeMode, AVPlaybackStatus } from 'expo-av';
import { playerEngine } from '../../player/playerEngine';
import { useVideoPlayerStore } from '../../store/videoStore';

export const GlobalVideoPlayer: React.FC = () => {
    const { updateTime, updateDuration, updatePlayState, updateSessionStatus, isEngineClaimedByLocal } = useVideoPlayerStore();

    if (isEngineClaimedByLocal) {
        return null;
    }

    if (Platform.OS === 'web') {
        return (
            <WebVideoPlayer
                updateTime={updateTime}
                updateDuration={updateDuration}
                updatePlayState={updatePlayState}
                updateSessionStatus={updateSessionStatus}
            />
        );
    }

    return (
        <NativeVideoPlayer
            updateTime={updateTime}
            updateDuration={updateDuration}
            updatePlayState={updatePlayState}
            updateSessionStatus={updateSessionStatus}
        />
    );
};

interface PlayerProps {
    updateTime: (t: number) => void;
    updateDuration: (d: number) => void;
    updatePlayState: (p: boolean) => void;
    updateSessionStatus: (status: any) => void;
}

const NativeVideoPlayer: React.FC<PlayerProps> = ({ updateTime, updateDuration, updatePlayState, updateSessionStatus }) => {
    const { activeVideo } = useVideoPlayerStore();

    const setRef = useCallback((instance: Video | null) => {
        playerEngine.getRef().current = instance;
    }, []);

    const initialStatus = {
        positionMillis: (activeVideo?.lastKnownPosition || 0) * 1000,
        shouldPlay: activeVideo?.isPlaying || false
    };

    return (
        <View style={styles.container} pointerEvents="none">
            <Video
                ref={setRef}
                style={styles.hiddenVideo}
                resizeMode={ResizeMode.CONTAIN}
                source={activeVideo?.videoUrl ? { uri: activeVideo.videoUrl } : undefined}
                status={initialStatus as any}
                onPlaybackStatusUpdate={(status: AVPlaybackStatus) => {
                    playerEngine.onStatusUpdate(status);
                    if (status.isLoaded) {
                        updateTime(status.positionMillis / 1000);
                        updateDuration(status.durationMillis ? status.durationMillis / 1000 : 0);
                        updatePlayState(status.isPlaying);

                        if (status.didJustFinish) updateSessionStatus('ended');
                        else if (status.isBuffering) updateSessionStatus('buffering');
                        else if (status.isPlaying) updateSessionStatus('playing');
                        else updateSessionStatus('paused');
                    } else if (status.error) {
                        updateSessionStatus('error');
                    }
                }}
                progressUpdateIntervalMillis={500}
            />
        </View>
    );
};

const WebVideoPlayer: React.FC<PlayerProps> = ({ updateTime, updateDuration, updatePlayState, updateSessionStatus }) => {
    const { activeVideo } = useVideoPlayerStore();
    const videoElRef = React.useRef<HTMLVideoElement | null>(null);

    useEffect(() => {
        const el = videoElRef.current;
        if (!el || !activeVideo?.videoUrl) return;

        el.src = activeVideo.videoUrl;
        el.currentTime = activeVideo.lastKnownPosition || 0;
        if (activeVideo.isPlaying) {
            el.play().catch(() => {});
        }
    }, [activeVideo?.videoUrl]);

    useEffect(() => {
        const el = videoElRef.current;
        if (!el) return;

        const onTimeUpdate = () => {
            updateTime(el.currentTime);
            updatePlayState(!el.paused);
        };
        const onLoadedMetadata = () => updateDuration(el.duration || 0);
        const onPlay = () => { updatePlayState(true); updateSessionStatus('playing'); };
        const onPause = () => { updatePlayState(false); updateSessionStatus('paused'); };
        const onWaiting = () => updateSessionStatus('buffering');
        const onEnded = () => updateSessionStatus('ended');
        const onError = () => updateSessionStatus('error');

        el.addEventListener('timeupdate', onTimeUpdate);
        el.addEventListener('loadedmetadata', onLoadedMetadata);
        el.addEventListener('play', onPlay);
        el.addEventListener('pause', onPause);
        el.addEventListener('waiting', onWaiting);
        el.addEventListener('ended', onEnded);
        el.addEventListener('error', onError);

        return () => {
            el.removeEventListener('timeupdate', onTimeUpdate);
            el.removeEventListener('loadedmetadata', onLoadedMetadata);
            el.removeEventListener('play', onPlay);
            el.removeEventListener('pause', onPause);
            el.removeEventListener('waiting', onWaiting);
            el.removeEventListener('ended', onEnded);
            el.removeEventListener('error', onError);
        };
    }, [updateTime, updateDuration, updatePlayState, updateSessionStatus]);

    const setVideoRef = useCallback((el: HTMLVideoElement | null) => {
        videoElRef.current = el;
        playerEngine.setWebVideoElement(el);
    }, []);

    return (
        <div style={{ position: 'absolute', width: 1, height: 1, opacity: 0, overflow: 'hidden', pointerEvents: 'none' }}>
            <video
                ref={setVideoRef}
                style={{ width: 1, height: 1 }}
                playsInline
            />
        </div>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        width: 1,
        height: 1,
        opacity: 0,
    },
    hiddenVideo: {
        width: 1,
        height: 1,
    }
});
