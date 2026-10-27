import { Linking } from 'react-native';
import { router } from 'expo-router';

export const navigate = (href: string) => {
  if (href.startsWith('http')) {
    Linking.openURL(href);
  } else {
    router.push(href as any);
  }
};
